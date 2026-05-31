# src/distributed_training.py
# ============================================================================
# PYTORCH DISTRIBUTED TRAINING: HUẤN LUYỆN PHÂN TÁN SONG SONG DỮ LIỆU (DDP)
# (Phục vụ làm tư liệu / thuật toán cho Báo cáo thuyết minh Đồ án)
# ============================================================================
#
# MỤC ĐÍCH:
#   Trình bày giải pháp mở rộng (scalability) khi lượng dữ liệu lịch sử chứng khoán
#   ở Batch Layer trở nên cực lớn qua nhiều năm.
#   Sử dụng giải pháp PyTorch Distributed Data Parallel (DDP) để huấn luyện mô hình
#   lai Hybrid LSTM-GNN song song phân tán trên cụm nhiều GPU/máy chủ (worker nodes).
#
# PHÂN BIỆT HAI CƠ CHẾ HUẤN LUYỆN PHÂN TÁN CHÍNH:
#
# 1. DATA PARALLELISM (Song song dữ liệu - Áp dụng trong đồ án này):
#    - Kiến trúc mô hình được sao chép nguyên vẹn trên mỗi GPU (worker node).
#    - Dữ liệu huấn luyện (Mini-batch) được chia nhỏ (DistributedSampler) và gửi
#      đến các GPU khác nhau xử lý song song.
#    - Cuối forward pass, các GPU đồng bộ gradient (All-Reduce operation) để
#      cập nhật trọng số đồng nhất trên toàn hệ thống.
#
# 2. MODEL PARALLELISM (Song song mô hình):
#    - Áp dụng khi mô hình quá lớn (ví dụ LLM hàng chục tỷ tham số) không thể
#      chứa vừa trong bộ nhớ (VRAM) của một GPU duy nhất.
#    - Các lớp (layers) hoặc nhánh của mô hình được cắt nhỏ và phân bổ trên
#      các GPU khác nhau (ví dụ: GPU 0 giữ LSTM, GPU 1 giữ GNN).
#
# ============================================================================

import os
import torch
import torch.nn as nn
import torch.distributed as dist
from torch.utils.data import DataLoader
from torch.utils.data.distributed import DistributedSampler
from torch.nn.parallel import DistributedDataParallel as DDP

from src.models import HybridLSTMGNNGraphGate


def setup_distributed_environment(rank: int, world_size: int):
    """
    Khởi tạo môi trường huấn luyện phân tán.

    Parameters
    ----------
    rank : int
        Chỉ số định danh duy nhất của GPU/Process hiện tại (0, 1, ..., world_size-1)
    world_size : int
        Tổng số GPU/Process tham gia huấn luyện phân tán
    """
    # IP/Port của Master node để điều phối giao tiếp và đồng bộ gradient
    os.environ["MASTER_ADDR"] = "127.0.0.1"  # Hoặc IP máy chủ chính
    os.environ["MASTER_PORT"] = "12355"      # Port giao tiếp trống

    # Sử dụng NCCL (NVIDIA Collective Communications Library) làm backend truyền tin
    # NCCL tối ưu cực mạnh cho truyền thông liên GPU qua kết nối NVLink hoặc mạng PCIe.
    # Sử dụng 'gloo' làm fallback nếu chạy trên CPU.
    backend = "nccl" if torch.cuda.is_available() else "gloo"
    
    dist.init_process_group(
        backend=backend,
        init_method="env://",
        rank=rank,
        world_size=world_size
    )
    
    if torch.cuda.is_available():
        torch.cuda.set_device(rank)
        print(f"[ddp] Process rank {rank} khởi tạo thành công trên GPU: {torch.cuda.get_device_name(rank)}")


def cleanup_distributed_environment():
    """Giải phóng tiến trình phân tán khi kết thúc huấn luyện."""
    dist.destroy_process_group()


def train_epoch_ddp(model, loader, optimizer, criterion, device, rank):
    """Một epoch huấn luyện phân tán sử dụng DDP."""
    model.train()
    total_loss = 0.0

    for batch in loader:
        # Load dữ liệu lên đúng GPU mà process này quản lý
        seq, node_x, adj, y_close, last_close = [x.to(device) for x in batch]

        optimizer.zero_grad()
        
        # Forward pass (chạy song song trên mỗi GPU với mini-batch riêng)
        pred_close = model(seq, node_x, adj, last_close)
        loss = criterion(pred_close, y_close)
        
        # Backward pass
        # DDP tự động kích hoạt phép toán All-Reduce để tính trung bình cộng
        # gradient giữa tất cả các GPU tham gia huấn luyện ngay khi loss.backward() chạy.
        loss.backward()
        
        optimizer.step()
        total_loss += loss.item()

    return total_loss / len(loader)


def run_distributed_training(rank: int, world_size: int, dataset):
    """
    Hàm thực thi chính cho huấn luyện phân tán trên từng worker.

    Parameters
    ----------
    rank : int
        GPU rank hiện tại
    world_size : int
        Tổng số GPU
    dataset : torch.utils.data.Dataset
        Dataset đồ thị cổ phiếu
    """
    # 1. Thiết lập môi trường giao tiếp liên GPU
    setup_distributed_environment(rank, world_size)

    # Xác định device
    device = torch.device(f"cuda:{rank}" if torch.cuda.is_available() else "cpu")

    # 2. Khởi tạo mô hình lai Hybrid LSTM-GNN
    raw_model = HybridLSTMGNNGraphGate(
        seq_input_dim=1,
        node_input_dim=7,
        lstm_hidden=64,
        gnn_hidden=32,
        mlp_hidden=64,
        dropout=0.2
    ).to(device)

    # 3. Bọc mô hình bằng lớp DistributedDataParallel (DDP)
    # DDP quản lý việc đồng bộ hóa trọng số ban đầu và tự động All-Reduce gradient
    # trong quá trình backward pass.
    model = DDP(raw_model, device_ids=[rank] if torch.cuda.is_available() else None)

    # 4. Sử dụng DistributedSampler chia nhỏ dữ liệu
    # Đảm bảo mỗi GPU chỉ nhận được phần dữ liệu không trùng lặp
    sampler = DistributedSampler(
        dataset,
        num_replicas=world_size,
        rank=rank,
        shuffle=True,
        seed=42
    )

    # DataLoader phân tán
    loader = DataLoader(
        dataset,
        batch_size=16,
        shuffle=False,  # Bắt buộc False vì sampler đã handle shuffle
        sampler=sampler,
        num_workers=2,
        pin_memory=True
    )

    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.MSELoss()

    epochs = 10
    print(f"[ddp-rank-{rank}] Bắt đầu huấn luyện...")
    for epoch in range(1, epochs + 1):
        # Thiết lập epoch cho sampler (để shuffle dữ liệu khác nhau mỗi epoch)
        sampler.set_epoch(epoch)

        loss = train_epoch_ddp(model, loader, optimizer, criterion, device, rank)
        
        # Chỉ in log từ rank 0 để tránh in trùng lặp trên console
        if rank == 0:
            print(f"Epoch {epoch:02d}/{epochs} | Average DDP Loss = {loss:.6f}")

    # 5. Giải phóng môi trường phân tán
    cleanup_distributed_environment()
    print(f"[ddp-rank-{rank}] Hoàn tất huấn luyện phân tán.")


# ============================================================================
# CƠ CHẾ KHỞI CHẠY ĐA TIẾN TRÌNH TRÊN BATCH LAYER SERVER
# ============================================================================
if __name__ == "__main__":
    # Giả lập để minh họa cách khởi chạy đa tiến trình
    print("=" * 80)
    print("DEMO CƠ CHẾ HUẤN LUYỆN PHÂN TÁN SONG SONG DỮ LIỆU TRÊN CỤM GPU")
    print("=" * 80)
    print("Để khởi chạy trong thực tế, sử dụng lệnh CLI:")
    print("  python -m torch.distributed.run --nproc_per_node=4 src/distributed_training.py")
    print("\nTrong đó --nproc_per_node=4 sẽ tự động spawn 4 processes tương ứng 4 GPU")
    print("=" * 80)
