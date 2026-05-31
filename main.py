#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
IE212 Stock Prediction System - Unified Bootstrapper
File main.py tự động hóa 100% quy trình thiết lập, chạy Stack và khởi chạy Frontend.
"""

import os
import sys
import subprocess
import time
import shutil
import platform

def log(message: str, level: str = "INFO"):
    colors = {
        "INFO": "[INFO]",
        "SUCCESS": "[SUCCESS]",
        "WARNING": "[WARNING]",
        "ERROR": "[ERROR]"
    }
    prefix = colors.get(level, f"[{level}]")
    try:
        print(f"{prefix} {message}")
    except UnicodeEncodeError:
        # Fallback for systems where sys.stdout encoding does not support full UTF-8 (e.g. cp1252 on windows terminal)
        safe_msg = message.encode("ascii", "replace").decode("ascii")
        print(f"{prefix} {safe_msg}")

def check_command(cmd: str) -> bool:
    try:
        subprocess.run([cmd, "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except FileNotFoundError:
        return False

def run_cmd(cmd: list, cwd: str = None, shell: bool = False, check: bool = True) -> subprocess.CompletedProcess:
    log(f"Đang chạy lệnh: {' '.join(cmd) if isinstance(cmd, list) else cmd} trong thư mục {cwd or 'gốc'}")
    return subprocess.run(cmd, cwd=cwd, shell=shell, check=check)

def main():
    log("=== KHỞI ĐỘNG HỆ THỐNG DỰ BÁO GIÁ CỔ PHIẾU IE212 ===", "SUCCESS")
    
    is_windows = platform.system().lower() == "windows"
    
    # 1. Kiểm tra các phần mềm bắt buộc
    if not check_command("docker"):
        log("Docker chưa được cài đặt hoặc chưa được khởi động! Vui lòng cài Docker Desktop trước.", "ERROR")
        sys.exit(1)
        
    if not check_command("npm"):
        log("NodeJS/NPM chưa được cài đặt! Vui lòng cài NodeJS trước để chạy Frontend.", "WARNING")
        
    # 2. Sao chép cấu hình .env nếu chưa có
    env_example = os.path.join("compose", ".env.example")
    env_target = os.path.join("compose", ".env")
    if not os.path.exists(env_target):
        log("Không tìm thấy file cấu hình compose/.env. Đang tự động tạo từ .env.example...")
        shutil.copy(env_example, env_target)
        log("Đã tạo file compose/.env thành công!", "SUCCESS")
    else:
        log("File compose/.env đã tồn tại, bỏ qua bước tạo.")

    # 3. Tạo virtual environment và cài đặt thư viện Python nếu chưa có
    venv_dir = ".venv"
    pip_path = os.path.join(venv_dir, "Scripts", "pip") if is_windows else os.path.join(venv_dir, "bin", "pip")
    python_path = os.path.join(venv_dir, "Scripts", "python") if is_windows else os.path.join(venv_dir, "bin", "python")
    
    if not os.path.exists(venv_dir):
        log("Đang tạo môi trường ảo Python Virtual Environment (.venv)...")
        run_cmd([sys.executable, "-m", "venv", venv_dir])
        log("Đang cài đặt các thư viện phụ thuộc từ requirements.txt...")
        run_cmd([pip_path, "install", "-r", "requirements.txt"])
        log("Đã chuẩn bị xong môi trường Python (.venv)!", "SUCCESS")
    else:
        log("Môi trường ảo (.venv) đã có sẵn, bỏ qua bước khởi tạo.")

    # 4. Huấn luyện mô hình cục bộ để chuẩn bị dữ liệu thô và file Checkpoint
    checkpoint_file = os.path.join("models", "hybrid_expanding_best_full.pt")
    raw_data_dir = os.path.join("data", "raw")
    if not os.path.exists(checkpoint_file) or not os.path.exists(raw_data_dir) or not os.listdir(raw_data_dir):
        log("Thiếu dữ liệu thô hoặc file mô hình. Đang kéo dữ liệu và huấn luyện mô hình cục bộ...")
        run_cmd([python_path, os.path.join("scripts", "run_train.py")])
        run_cmd([python_path, os.path.join("scripts", "run_experiment.py")])
        log("Đã huấn luyện xong mô hình cục bộ và lưu trữ checkpoint!", "SUCCESS")
    else:
        log("Mô hình và dữ liệu thô đã có sẵn, bỏ qua bước huấn luyện.")

    # 5. Khởi động Docker Big Data Stack
    log("Đang tiến hành dựng và khởi động Docker Big Data Stack...", "SUCCESS")
    
    # 5.1. Build Airflow Image Custom
    log("Build Airflow Custom Image...")
    run_cmd(["docker", "build", "-t", "ie212-airflow-custom:local", "-f", "airflow/Dockerfile", "."])
    
    # 5.2. Khởi chạy toàn bộ stack và stock-producer
    log("Khởi động hệ thống Docker Compose...")
    run_cmd(["docker", "compose", "--env-file", "compose/.env", "-f", "compose/compose.yaml", "--profile", "producer", "up", "-d", "--build"])
    
    # 5.3. Tạo Database airflow_meta và chạy migration
    log("Khởi tạo cơ sở dữ liệu Airflow Metadata...")
    # Đợi Postgres sẵn sàng nhận kết nối
    log("Đợi PostgreSQL container khởi động ổn định...")
    time.sleep(10)
    
    try:
        run_cmd(["docker", "exec", "ie212-postgres", "psql", "-U", "stock_user", "-d", "postgres", "-c", "CREATE DATABASE airflow_meta OWNER stock_user;"], check=False)
    except Exception:
        pass # Database might already exist
        
    run_cmd(["docker", "compose", "--env-file", "compose/.env", "-f", "compose/compose.yaml", "up", "-d", "airflow-init"])
    
    # Đợi airflow-init chạy hoàn tất
    log("Đợi Airflow database migration chạy xong...")
    time.sleep(12)
    
    # 5.4. Khởi động Airflow Services khác
    log("Khởi động Airflow Scheduler, Triggerer và Dag Processor...")
    run_cmd(["docker", "compose", "--env-file", "compose/.env", "-f", "compose/compose.yaml", "up", "-d", "airflow-apiserver", "airflow-scheduler", "airflow-dag-processor", "airflow-triggerer"])

    # 6. Tạo sẵn dữ liệu mô phỏng cho PostgreSQL để tránh lỗi Unhealthy/No Data ở dashboard
    log("Đang tự động xuất bản gói tin Kafka ban đầu và kích hoạt chạy PyTorch Inference để PostgreSQL có sẵn dữ liệu...", "SUCCESS")
    try:
        # Xuất bản bản tin Kafka
        run_cmd([python_path, os.path.join("scripts", "publish_stock_ticks.py"), "--bootstrap-servers", "localhost:29092", "--source", "csv", "--max-iterations", "1"])
        # Chạy PyTorch Inference ghi vào Postgres
        log("Đang chạy mô hình AI Dự đoán giá trực tiếp và nạp dữ liệu vào bảng stock.inference_predictions...")
        run_cmd(["docker", "exec", "ie212-ml-infer", "python", "scripts/build_kafka_inference_bundle.py"])
        # Lưu vào Postgres
        run_cmd(["docker", "exec", "ie212-ml-infer", "python", "scripts/save_inference_to_postgres.py", "--input-json", "/workspace/outputs/inference/latest_prediction.json"])
        log("Nạp dữ liệu dự báo ban đầu thành công! PostgreSQL đã sẵn sàng dữ liệu.", "SUCCESS")
    except Exception as e:
        log(f"Không thể chạy luồng nạp dữ liệu tự động: {e}. Vui lòng tự chạy DAG trên Airflow sau.", "WARNING")

    log("Docker Big Data Stack đã chạy ổn định!", "SUCCESS")
    log("Địa chỉ hệ thống:", "INFO")
    log("- Airflow UI: http://localhost:8088 (admin/airflow)", "INFO")
    log("- FastAPI / Dashboard UI: http://localhost:8008/dashboard", "INFO")

    # 7. Khởi động Frontend React Local
    frontend_dir = "frontend"
    if os.path.exists(frontend_dir) and os.path.exists(os.path.join(frontend_dir, "package.json")):
        log("Phát hiện thư mục Frontend React. Đang tiến hành cài đặt node_modules và khởi chạy Frontend...", "SUCCESS")
        try:
            # Install packages
            log("Đang chạy npm install cho Frontend...")
            run_cmd(["npm", "install"], cwd=frontend_dir, shell=is_windows)
            # Start dev server
            log("Khởi động Frontend React dev server...", "SUCCESS")
            run_cmd(["npm", "run", "dev"], cwd=frontend_dir, shell=is_windows)
        except KeyboardInterrupt:
            log("Đã dừng Frontend dev server.", "WARNING")
        except Exception as e:
            log(f"Lỗi khi khởi chạy React Frontend: {e}. Bạn có thể truy cập Dashboard chính tại http://localhost:8008/dashboard", "ERROR")
    else:
        log("Không tìm thấy thư mục React Frontend hoặc thiếu package.json. Hệ thống chạy trên Dashboard FastAPI mặc định tại http://localhost:8008/dashboard", "WARNING")

if __name__ == "__main__":
    main()
