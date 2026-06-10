# Mô Tả Chi Tiết Các Tệp Tin Python (`.py`) Trong Dự Án IE212

Tài liệu này cung cấp mô tả chi tiết, chức năng cốt lõi và vai trò của từng tệp tin Python (`.py`) trong cấu trúc thư mục của dự án **IE212 - Hệ thống dự báo giá cổ phiếu bằng mô hình lai thích ứng Hybrid LSTM-GNN kết hợp Big Data Pipeline (Kafka, Spark, Airflow, MinIO, PostgreSQL)**.

---

## 📌 1. Thư mục gốc (Root)

### `D:/ie212/main.py`
* **Mô tả:** Tệp tin khởi chạy hợp nhất (unified bootstrapper) đóng vai trò là "nhạc trưởng" của toàn bộ dự án. Nhiệm vụ của nó là ẩn đi sự phức tạp của hệ thống Big Data và Machine Learning, cung cấp cho người dùng một quy trình tự động hóa 100% chỉ qua một lệnh chạy duy nhất.
* **Chức năng chính:** Điều phối toàn bộ vòng đời khởi động hệ thống từ kiểm tra môi trường, cài đặt thư viện, huấn luyện mô hình cơ sở, triển khai hạ tầng Docker cho đến khởi động giao diện người dùng.
* **Cách thực hiện:**
  - **Kiểm tra môi trường:** Chạy lệnh subprocess để kiểm tra sự tồn tại của `docker` và `npm`. Nếu thiếu, hệ thống sẽ cảnh báo và dừng lại.
  - **Cấu hình biến môi trường:** Kiểm tra thư mục `compose/` và tự động copy file `.env.example` thành `.env` nếu chưa tồn tại.
  - **Quản lý Python Virtual Environment:** Tự động tạo thư mục `.venv` bằng module `venv`, sau đó dùng pip cài đặt các thư viện phụ thuộc từ `requirements.txt`.
  - **Khởi tạo dữ liệu & Huấn luyện (Cold Start):** Kiểm tra thư mục `data/raw` và file `models/hybrid_expanding_best_full.pt`. Nếu chưa có dữ liệu thô hoặc mô hình, file sẽ gọi script `scripts/run_train.py` để kéo dữ liệu và `scripts/run_experiment.py` để train mô hình ban đầu.
  - **Khởi động Big Data Stack:** Sử dụng `docker compose` (với file `compose/compose.yaml`) để dựng toàn bộ các container (Kafka, Spark, MinIO, PostgreSQL, Airflow). Tự động tạo database `airflow_meta` và chờ migration hoàn tất.
  - **Mock Data & Khởi tạo dự đoán:** Chạy script `publish_stock_ticks.py` để đưa dữ liệu giả vào Kafka và thực thi bundle suy luận thông qua container `ie212-ml-infer`, đảm bảo khi dashboard lên hình sẽ có sẵn dữ liệu thay vì lỗi kết nối.
  - **Khởi chạy Frontend:** Chạy lệnh `npm install` và `npm run dev` trong thư mục `frontend/` để mở giao diện Web giám sát (Dashboard).

---

## 🛠️ 2. Thư mục `src/` (Mô hình & Xử lý dữ liệu)

### `D:/ie212/src/config.py`
* **Mô tả:** Đóng vai trò là trung tâm điều khiển tham số (Central Configuration) cho toàn bộ mã nguồn mô hình Hybrid LSTM-GNN. Việc thay đổi thuật toán, khoảng thời gian hay cấu trúc mạng đều thực hiện tại đây.
* **Chức năng chính:** Cung cấp hằng số cho danh sách cổ phiếu (`TICKERS`), ngưỡng ngày, cấu trúc mạng (`LSTM_HIDDEN`, `GNN_HIDDEN`), tham số backtest (`EXP_TEST_DAYS`, `LOOKBACK`) và lịch trình Airflow (`RETRAIN_SCHEDULE`).
* **Cách thực hiện:** Tệp chỉ chứa các biến hằng số Python (Pure Constants) tĩnh mà không có lớp hay hàm xử lý logic. Các tệp khác sẽ `import` trực tiếp biến từ đây.

### `D:/ie212/src/data_loader.py`
* **Mô tả:** Module thu thập, làm sạch và đồng bộ hóa chuỗi dữ liệu thời gian cho danh mục cổ phiếu từ nguồn internet hoặc bộ đệm (cache) cục bộ.
* **Chức năng chính:** Tải dữ liệu, tính toán chỉ báo và căn chỉnh trục thời gian.
* **Cách thực hiện:**
  - Dùng API thư viện `yfinance` tải dữ liệu OHLCV (Open, High, Low, Close, Volume). Có cơ chế fallback dùng `.history()` nếu `.download()` lỗi.
  - Sử dụng Pandas DataFrame để điền giá trị khuyết thiếu (ffill/fillna) và trích xuất thêm 5 cột đặc trưng mới: `Return` (tỷ suất sinh lời), `MA5`, `MA20`, `Volatility5`, `Volatility20`.
  - Hàm `align_common_index` dùng phép giao (intersection) trên index của tất cả các cổ phiếu để loại bỏ những ngày giao dịch không trùng khớp, đảm bảo tensor đầu ra hoàn hảo.

### `D:/ie212/src/features.py`
* **Mô tả:** Bộ chuyển đổi dữ liệu từ dạng bảng (Pandas DataFrame) độc lập sang cấu trúc Tensor 3D đồng nhất phục vụ cho PyTorch DataLoader.
* **Chức năng chính:** Trích xuất mảng NumPy đa chiều từ bộ từ điển (dictionary) các DataFrame.
* **Cách thực hiện:** Hàm `build_feature_tensor` khởi tạo các mảng NumPy rỗng kích thước `[T, N, F]` (Thời gian $\times$ Số cổ phiếu $\times$ Số đặc trưng). Sau đó, nó duyệt qua từng mã cổ phiếu để đổ dữ liệu đặc trưng vào trục `N` tương ứng, đồng thời tách riêng mảng mục tiêu `Close` và mảng `Return`.

### `D:/ie212/src/graph_builder.py`
* **Mô tả:** Engine xây dựng cấu trúc Đồ thị (Adjacency Matrix) đại diện cho ma trận tương tác và dẫn dắt giữa các mã cổ phiếu trong mạng GNN.
* **Chức năng chính:** Xây dựng, kết hợp, cắt tỉa (sparsify) và chuẩn hóa (normalize) ma trận kề $N \times N$.
* **Cách thực hiện:**
  - **Pearson Graph:** Dùng `np.corrcoef` đo lường tương quan độ lệch chuẩn của tỷ suất sinh lời, lọc bỏ các cạnh dưới ngưỡng `EXP_PEARSON_THRESHOLD`.
  - **Association Rules:** Tính toán xác suất tăng/giảm đồng thời. Dùng chỉ số Support, Confidence và Lift để phát hiện mối quan hệ kéo theo không đối xứng.
  - **Kết hợp & Chuẩn hóa:** Trộn hai ma trận với trọng số $\alpha$. Dùng hàm `sparsify_keep_topk` giữ lại tối đa $K$ cạnh kết nối mạnh nhất mỗi node, sau đó nhân ma trận đường chéo bậc $D^{-1/2}AD^{-1/2}$ để chống bùng nổ gradient.

### `D:/ie212/src/rolling_scaler.py`
* **Mô tả:** Lớp `RollingMinMaxScaler` chuẩn hóa động (Dynamic Scaling) thiết kế riêng để đối phó với hiện tượng "Data Drift" (trôi phân phối) trong dữ liệu chứng khoán.
* **Chức năng chính:** Chuẩn hóa dữ liệu về khoảng [0, 1] theo lô thời gian ngắn và đảo ngược chuẩn hóa cho giá dự đoán.
* **Cách thực hiện:** Thay vì dùng MinMaxScaler trên toàn bộ tập train (gây lệch lớn nếu giá tương lai bứt phá quá xa), lớp này duy trì một cửa sổ trượt $W$ ngày (VD: 60 ngày). Mức min/max chỉ tính trên $W$ ngày ngay trước ngày cần dự báo, giúp dữ liệu vào luôn ở tỷ lệ ổn định bất chấp xu hướng vĩ mô thay đổi. Cung cấp hàm `inverse_transform_close` để khôi phục giá trị thực.

### `D:/ie212/src/dataset.py`
* **Mô tả:** Wrapper đóng gói dữ liệu của dự án thành chuẩn `torch.utils.data.Dataset`.
* **Chức năng chính:** Ép kiểu, lưu trữ và cung cấp từng mẫu dữ liệu (sample) cho quá trình huấn luyện theo lô.
* **Cách thực hiện:** Hàm `__init__` nhận 6 mảng numpy (`X_seq`, `X_node`, `A`, `y_res`, `y_close`, `last_close`), ép về kiểu `torch.float32`. Hàm `__getitem__` trích xuất và trả về tuple chứa toàn bộ thông tin của 1 ngày (index) phục vụ cho một bước tiến của mạng thần kinh.

### `D:/ie212/src/models.py`
* **Mô tả:** Trái tim thuật toán của hệ thống, chứa các định nghĩa lớp mạng thần kinh (Neural Network Architecture) kế thừa từ `torch.nn.Module`.
* **Chức năng chính:** Xác định luồng truyền qua mạng (Forward pass) để đưa ra dự báo.
* **Cách thực hiện:**
  - `SimpleGCNLayer`: Thực hiện nhân ma trận giữa ma trận kề và vector đặc trưng nút (Aggregation).
  - `LSTMOnlyModel`: Kiến trúc đối chứng. Chuyển tensor chuỗi thời gian qua khối `nn.LSTM` trích xuất vector trạng thái ẩn, sau đó đi qua Linear layer dự đoán chênh lệch giá.
  - `HybridLSTMGNNGraphGate`: Kiến trúc phức hợp.
    1. Chuỗi thời gian đi qua khối LSTM.
    2. Đặc trưng tại thời điểm hiện tại đi qua 2 khối GCN để hấp thu thông tin liên đới.
    3. Cả hai vector hòa trộn tại một cổng Graph Gate (dùng Sigmoid để tự động quyết định mức độ tin tưởng vào GCN so với LSTM).
    4. Khối MLP cuối tính toán phần dư giá (Residual). Giá dự báo = Giá phiên trước + Phần dư.

### `D:/ie212/src/train_eval.py`
* **Mô tả:** Trình điều khiển vòng đời huấn luyện (Trainer) và tiện ích tương tác với mô hình.
* **Chức năng chính:** Điều khiển Epoch, tính Loss, dự báo, tối ưu Early Stopping và chuyển giao học (Transfer Learning).
* **Cách thực hiện:**
  - Hàm `train_one_epoch` dùng `optimizer.step()` và `loss.backward()` cập nhật trọng số, hỗ trợ kết hợp thêm Loss định hướng (Directional Loss) nếu cấu hình.
  - Hàm `fit_model_silent` chạy vòng lặp tối đa $N$ epochs. Nó theo dõi Validation Loss liên tục. Nếu sau `Patience` epochs (VD: 5) mà Loss không giảm, hệ thống Early Stopping kích hoạt, tự động rollback (khôi phục) lại trạng thái mô hình tốt nhất để chống quá khớp (Overfitting).
  - Hàm `initialize_hybrid_from_lstm_model`: Chép toàn bộ trọng số mảng LSTM đã được train sẵn vào mô hình Hybrid, giúp mô hình lai hội tụ cực kỳ nhanh.

### `D:/ie212/src/expanding.py`
* **Mô tả:** Triển khai thuật toán Đánh giá Cửa sổ mở rộng (Expanding Window Backtest) chống rò rỉ dữ liệu tương lai.
* **Chức năng chính:** Cắt lát mảng 3D tĩnh thành hàng nghìn khối dữ liệu (Samples) trượt dọc theo trục thời gian.
* **Cách thực hiện:** Hàm `prepare_expanding_step_data` đảm bảo mỗi khi cửa sổ dịch sang ngày $t$:
  1. Ma trận kề đồ thị được xây dựng lại chỉ với thông tin đến ngày $t-1$.
  2. Mức min/max của MinMaxScaler được đo lường lại.
  3. Dữ liệu huấn luyện, dữ liệu validation ($V$ ngày sát ngày $t$) và dữ liệu test (duy nhất ngày $t$) được tách rời hoàn toàn, nạp vào PyTorch Dataset.

### `D:/ie212/src/evaluation.py`
* **Mô tả:** Bảng điều khiển giám định đo lường cả độ chính xác toán học lẫn tỷ suất lợi nhuận tài chính.
* **Chức năng chính:** Cung cấp hàng loạt hàm đo lường metric tiêu chuẩn và giả lập chiến lược giao dịch thực tế.
* **Cách thực hiện:**
  - **Học máy (ML Metrics):** Tính MSE, RMSE, MAE, MAPE và $R^2$ dùng thư viện `sklearn`.
  - **Backtest (Financial Metrics):** Hàm `backtest_long_only_strategy` giả lập mua đều các mã dự đoán tăng và bán ra vào cuối ngày. Từ đó hệ thống tự động tính lũy kế lợi nhuận, Max Drawdown (tỷ lệ cháy tài khoản cao nhất) và Sharpe Ratio (Tỷ suất sinh lời trên rủi ro).
  - **So sánh:** Mọi thông số tài chính đều được so khớp (benchmark) trực tiếp với chiến lược nhắm mắt mua để đó (Buy-and-Hold).

### `D:/ie212/src/distributed_training.py`
* **Mô tả:** Động cơ xử lý phân tán (Distributed Data Parallel - DDP) khi dữ liệu mở rộng.
* **Chức năng chính:** Cho phép mô hình phân chia batch nạp dữ liệu huấn luyện đồng thời trên nhiều GPU/Node.
* **Cách thực hiện:** Khởi tạo môi trường mạng qua `dist.init_process_group` (dùng NCCL cho GPU hoặc Gloo cho CPU). Bọc mạng thần kinh bằng `DistributedDataParallel` và thay thế DataLoader thường bằng `DistributedSampler`. Lúc này tại bước `loss.backward()`, PyTorch tự động chạy All-Reduce đồng bộ hóa gradient chéo qua các card đồ họa.

### `D:/ie212/src/spark_features.py`
* **Mô tả:** Pipeline trích xuất đặc trưng trên kiến trúc dữ liệu khổng lồ (Big Data Feature Engineering).
* **Chức năng chính:** Ứng dụng Apache Spark SQL tính toán chỉ báo kỹ thuật phân tán cho hàng triệu điểm dữ liệu.
* **Cách thực hiện:** Dùng `pyspark.sql.window.Window` gom nhóm (partition) dữ liệu theo mã cổ phiếu và sắp xếp theo ngày. Kỹ thuật này tính RSI 14 ngày, đường trung bình trượt mũ (EMA) của MACD và dải Bollinger Bands chỉ với các phép biến đổi DataFrame (Transformations) song song trên các worker thay vì dùng vòng lặp For tuần tự chậm chạp.

### `D:/ie212/src/artifacts.py`
* **Mô tả:** Tiện ích thao tác trực tiếp với File System phục vụ lưu trữ trọng số.
* **Chức năng chính:** Lưu trữ, khôi phục Checkpoint PyTorch và xuất Meta Data.
* **Cách thực hiện:** Hàm `save_model_checkpoint` gói khối `state_dict` (từ điển trọng số của Neural Network) chung với một object metadata JSON (thời gian lưu, config). Dùng `torch.save`/`torch.load` ghi xuống đĩa, giúp bảo toàn chính xác trạng thái mô hình mà không cần thiết lập lại cấu trúc từ đầu.

---

## ⚡ 3. Thư mục `scripts/` (Kịch bản thực thi & Kiểm thử)

### `D:/ie212/scripts/_path_setup.py`
* **Mô tả:** Tiện ích thiết lập đường dẫn (Path Bootstrap) giải quyết vấn đề Python không thể import các module nằm ngoài thư mục hiện hành. Khi chạy một script bất kỳ trong `scripts/` (ví dụ `python scripts/test_model_forward.py`), Python mặc định chỉ tìm module trong thư mục `scripts/` — dẫn đến lỗi `ModuleNotFoundError: No module named 'src'`. File này khắc phục triệt để vấn đề đó.
* **Chức năng chính:** Xác định đường dẫn tuyệt đối đến thư mục gốc của dự án (Repository Root) và chèn nó vào đầu danh sách `sys.path` của Python, cho phép tất cả các script con import trực tiếp các module `src.config`, `src.models`, `src.data_loader`, v.v. mà không cần cài đặt package hay thao tác thủ công.
* **Cách thực hiện:**
  - Sử dụng `Path(__file__).resolve().parent.parent` để từ vị trí tệp hiện tại (`scripts/_path_setup.py`) đi ngược lên 2 cấp thư mục: `scripts/` → thư mục gốc `D:/ie212/`. Kết quả được lưu vào biến `REPO_ROOT`.
  - Kiểm tra xem `REPO_ROOT` đã tồn tại trong `sys.path` chưa. Nếu chưa, chèn vào vị trí đầu tiên (`index 0`) bằng `sys.path.insert(0, str(REPO_ROOT))` để đảm bảo ưu tiên cao nhất khi Python tìm kiếm module.
  - Các script khác chỉ cần thêm một dòng `import _path_setup` ở đầu file là toàn bộ thư mục `src/` trở nên khả dụng ngay lập tức.

### `D:/ie212/scripts/inspect_checkpoint.py`
* **Mô tả:** Công cụ tiện ích dòng lệnh (CLI Utility) giúp kiểm tra sâu và giải mã các thông số kỹ thuật bên trong của tệp checkpoint lưu trữ mô hình PyTorch (`.pt` hoặc `.pth`). Công cụ này cực kỳ hữu ích để gỡ lỗi cấu trúc mạng mà không cần nạp mô hình vào bộ nhớ hoặc chạy huấn luyện thực tế.
* **Chức năng chính:**
  - Nhận đường dẫn tệp checkpoint đầu vào, nạp và xác định kiểu dữ liệu.
  - Phân tích cấu trúc dữ liệu để định vị khóa chứa từ điển trọng số (`state_dict` hoặc `model_state_dict`).
  - Liệt kê và hiển thị kích thước (shape) của 20 lớp tham số trọng số đầu tiên.
  - Tự động suy luận kiến trúc mạng (tần số chuỗi, số node, số hidden của LSTM, GCN, MLP) dựa trên kích thước các ma trận trọng số.
* **Cách thực hiện:**
  - **Nhận tham số CLI:** Sử dụng thư viện `argparse` định nghĩa tham số bắt buộc `--checkpoint` nhận đường dẫn tới file cần kiểm tra.
  - **Nạp dữ liệu an toàn:** Dùng `torch.load(..., map_location="cpu")` để nạp tệp lên bộ nhớ CPU, tránh lỗi nếu checkpoint được huấn luyện trên GPU trước đó.
  - **Truy vết cấu trúc dữ liệu:** Kiểm tra xem biến nạp vào có phải là kiểu từ điển (`dict`) hay không. Duyệt qua các khóa để tìm kiếm `state_dict` hoặc `model_state_dict`. Nếu toàn bộ giá trị bên trong đều là Torch Tensor thì tự động suy luận tệp đó là một `raw state_dict`.
  - **Tự động suy luận kiến trúc:** Thực hiện các phép tính toán học ngược để suy ra cấu trúc mạng:
    - Kích thước chiều vào chuỗi `seq_input_dim` từ trục thứ 2 của `lstm.weight_ih_l0`.
    - Số neural ẩn `lstm_hidden` bằng chiều dài trục thứ nhất của `lstm.weight_ih_l0` chia cho 4 (do LSTM có 4 cổng F, I, C, O ghép lại).
    - Đặc trưng node đầu vào `node_input_dim` và `gnn_hidden` từ tầng chiếu `node_proj.weight`.
    - Lớp ẩn MLP `mlp_hidden` trích xuất từ tầng nơ-ron liên kết đầu tiên `mlp.0.weight`.
    - In các thông số cấu trúc trực quan ra console.

### `D:/ie212/scripts/publish_stock_ticks.py`
* **Mô tả:** Script Producer mô phỏng luồng dữ liệu giá cổ phiếu thời gian thực (Stock Tick Streaming) và đẩy các bản tin này vào Apache Kafka. Đây là thành phần đầu vào của Speed Layer trong kiến trúc Big Data, giúp hệ thống có dữ liệu realtime để Spark Streaming/Spark Batch tiêu thụ, xử lý và lưu trữ xuống PostgreSQL hoặc Parquet.
* **Chức năng chính:**
  - Nhận cấu hình chạy từ dòng lệnh hoặc biến môi trường: Kafka bootstrap server, topic, danh sách ticker, tần suất gửi dữ liệu, số vòng lặp tối đa, nguồn dữ liệu và chế độ dry-run.
  - Xác định danh sách mã cổ phiếu cần phát dữ liệu. Nếu người dùng không truyền `--tickers`, script sẽ ưu tiên biến môi trường `IE212_PRODUCER_TICKERS`, sau đó fallback về danh sách `TICKERS` trong `src.config`.
  - Lấy giá cổ phiếu từ 2 nguồn: `yfinance` để lấy giá gần nhất theo thị trường, hoặc file CSV cục bộ trong `data/raw` để chạy offline/replay khi không có internet.
  - Đóng gói mỗi giá cổ phiếu thành JSON message gồm `symbol`, `price`, `event_time`, `source`.
  - Tạo Kafka Producer có retry, serializer cho key/value, xác nhận gửi tin bằng `acks="all"`, và đẩy message vào topic mặc định `stock-price`.
  - Hỗ trợ chế độ `--dry-run` để chỉ in ra message sẽ gửi mà không cần kết nối Kafka, rất hữu ích cho debug.
* **Cách thực hiện:**
  - **Bước 1 - Đọc tham số:** Hàm `parse_args()` dùng `argparse` định nghĩa các tham số như `--bootstrap-servers`, `--topic`, `--tickers`, `--interval-seconds`, `--max-iterations`, `--source`, `--csv-dir`, `--dry-run`. Mỗi tham số đều có giá trị mặc định lấy từ biến môi trường hoặc fallback nội bộ.
  - **Bước 2 - Xác định ticker:** Hàm `resolve_tickers()` chuẩn hóa danh sách ticker về chữ hoa. Thứ tự ưu tiên là tham số CLI → biến môi trường → `src.config.TICKERS`.
  - **Bước 3 - Lấy giá:** Hàm `resolve_price()` chọn nguồn dữ liệu theo `--source`:
    - `yfinance`: gọi `get_price_from_yfinance()`, ưu tiên `fast_info` rồi fallback sang lịch sử 5 ngày gần nhất.
    - `csv`: gọi `get_price_from_csv()`, đọc dòng cuối cùng trong file `{ticker}.csv` và lấy cột `Close`.
    - `auto`: thử `yfinance` trước, nếu lỗi thì tự động fallback về CSV.
  - **Bước 4 - Tạo message:** Hàm `build_message()` tạo dictionary JSON gồm mã cổ phiếu, giá đã làm tròn 4 chữ số thập phân, thời điểm sự kiện theo UTC ISO format và nguồn sinh dữ liệu.
  - **Bước 5 - Kết nối Kafka:** Hàm `create_producer()` dùng `kafka.KafkaProducer`, thiết lập `bootstrap_servers`, `client_id`, `acks="all"`, `retries=5`, `value_serializer=json.dumps(...).encode("utf-8")`, `key_serializer=key.encode("utf-8")`. Nếu Kafka chưa sẵn sàng, hàm sẽ thử lại theo `--connect-retries` và `--retry-delay-seconds`.
  - **Bước 6 - Gửi dữ liệu:** Hàm `publish_round()` duyệt từng ticker, lấy giá, build message, gửi vào topic Kafka bằng `producer.send(topic, key=ticker, value=message)`, chờ metadata xác nhận offset/partition bằng `future.get(timeout=20)`, sau đó `flush()` để đảm bảo dữ liệu được đẩy đi.
  - **Bước 7 - Vòng lặp streaming:** Hàm `main()` chạy vòng lặp vô hạn hoặc dừng theo `--max-iterations`. Sau mỗi vòng gửi, script ngủ `--interval-seconds` giây rồi tiếp tục vòng tiếp theo. Khi người dùng nhấn `Ctrl+C`, producer được `flush()` và `close()` an toàn.

### `D:/ie212/scripts/sync_parquet_to_minio.py`
* **Mô tả:** Script chịu trách nhiệm đồng bộ hóa các tệp tin dữ liệu Parquet từ hệ thống lưu trữ cục bộ lên máy chủ lưu trữ đối tượng MinIO (Object Storage tương thích S3). Đây là thành phần cầu nối giúp di chuyển dữ liệu từ Speed Layer/Batch Layer cục bộ lên hệ thống Data Lake đám mây phục vụ cho việc lưu trữ phân tán lâu dài và làm đầu vào cho các tác vụ huấn luyện/dự báo định kỳ của Airflow.
* **Chức năng chính:**
  - Khởi tạo kết nối S3 Client tương thích chuẩn MinIO.
  - Tự động kiểm tra và tạo bucket đích trên MinIO nếu chưa tồn tại.
  - Xóa sạch các đối tượng cũ theo đường dẫn chỉ định (Prefix) trước khi tải dữ liệu mới lên để tránh dư thừa và xung đột dữ liệu cũ.
  - Đệ quy duyệt thư mục Parquet cục bộ, kiểm tra an toàn để chặn việc upload nhầm các thư mục làm việc lớn (Workspace), thực hiện ánh xạ đường dẫn tương đối và tải toàn bộ tệp Parquet lên MinIO.
* **Cách thực hiện:**
  - **Hàm `create_s3_client()`:** Khởi tạo `boto3.client('s3', ...)` với cấu hình `endpoint_url` (địa chỉ cổng MinIO), `aws_access_key_id`, `aws_secret_access_key`. Thiết lập `signature_version="s3v4"` và `s3={"addressing_style": "path"}` để tương thích tuyệt đối với dịch vụ MinIO tự dựng cục bộ.
  - **Hàm `ensure_bucket()`:** Gọi `client.list_buckets()` lấy danh sách bucket hiện có. Nếu bucket đích (VD: `stock-parquet`) chưa có trong danh sách, gọi `client.create_bucket()` để tự động tạo mới.
  - **Hàm `delete_prefix()`:** Sử dụng `client.get_paginator("list_objects_v2")` để quét phân trang toàn bộ các tệp tin hiện tại khớp với tiền tố (`Prefix`). Nếu tìm thấy, thực hiện gọi `client.delete_objects()` xóa hàng loạt nhằm dọn dẹp thư mục đích trên MinIO trước khi đồng bộ.
  - **Hàm `upload_directory()`:**
    1. Chuyển đổi đường dẫn thư mục cục bộ về dạng tuyệt đối bằng `.resolve()`.
    2. Chặn upload nguy hiểm: So sánh nếu thư mục nguồn là `/workspace` hoặc `.` (thư mục gốc dự án) thì lập tức nâng lỗi `ValueError` từ chối thực thi để bảo vệ an toàn dữ liệu, tránh tải lên hàng GB tệp tin không liên quan.
    3. Tìm kiếm đệ quy toàn bộ tệp bằng `.rglob("*")`, sắp xếp danh sách và tính toán đường dẫn tương đối `.relative_to()`.
    4. Gọi `client.upload_file()` để đẩy từng tệp Parquet lên đám mây với khóa dạng `prefix/relative_path.parquet`.
  - **Hàm `main()`:** Dùng `argparse` định nghĩa 6 tham số CLI: `--local-dir`, `--minio-endpoint`, `--access-key`, `--secret-key`, `--bucket`, `--prefix`. Thực hiện kiểm tra sự tồn tại của thư mục cục bộ, tuần tự gọi khởi tạo Client → Ensure Bucket → Dọn dẹp Prefix → Upload Directory và in báo cáo số lượng file đã đồng bộ thành công.

### `D:/ie212/scripts/build_latest_inference_bundle.py`
* **Mô tả:** Script xây dựng gói dữ liệu phục vụ dự báo ngoại tuyến (Offline Inference Bundle) từ nguồn dữ liệu CSV cục bộ hiện tại. Đây là bước tiền xử lý cuối cùng trước khi đưa dữ liệu vào mô hình Machine Learning, giúp định hình cấu trúc tensor đồng bộ 100% với môi trường huấn luyện.
* **Chức năng chính:**
  - Nạp dữ liệu giá chứng khoán thô từ thư mục cục bộ.
  - Căn chỉnh trục thời gian chung giữa các mã cổ phiếu và tính toán các đặc trưng kỹ thuật liên quan.
  - Áp dụng MinMaxScaler động trên cửa sổ trượt (Rolling MinMaxScaler) và trích xuất chuỗi lịch sử cho LSTM.
  - Tạo lập ma trận kề đồ thị Pearson kết hợp Association Rules và xuất gói dữ liệu định dạng `.npz` nén.
* **Cách thực hiện:**
  - **Hàm `read_one_csv()`:** Đọc tệp CSV, tự động dò tìm và chuẩn hóa cột thời gian, lọc cột OHLCV, tính toán 5 chỉ báo mở rộng (`Return`, `MA5`, `MA20`, `Volatility5`, `Volatility20`) và sắp xếp theo trục thời gian tăng dần.
  - **Hàm `main()`:**
    1. Quét toàn bộ tệp `.csv` trong `--data-dir` (mặc định `data/raw`) để lấy danh sách ticker.
    2. Căn chỉnh ngày chung (`common_index`), reindex các DataFrame và chuyển đổi thành Tensor thô `[T, N, F]`.
    3. Khởi tạo `RollingMinMaxScaler(window_size=60)`, fit-transform dữ liệu để tránh Data Leakage.
    4. Trích xuất chuỗi Close có độ dài trượt `LOOKBACK` (mặc định 20 ngày) ở thời điểm hiện tại `t_last` và định hình chiều thành `[1, N, lookback, 1]`.
    5. Xây dựng đồ thị liên kết ngành hỗn hợp dựa trên dữ liệu tỷ suất sinh lời của 2 năm giao dịch gần nhất `[t_last - 504, t_last]`.
    6. Lưu tất cả mảng NumPy (`X_seq`, `X_node`, `A`, `last_close`, `tickers`, `as_of_date`, `adj_raw`, `feature_cols` và tham số của scaler) vào tệp `.npz` đích.

### `D:/ie212/scripts/build_kafka_inference_bundle.py`
* **Mô tả:** Script đóng gói dữ liệu phục vụ dự báo trực tuyến (Real-time Inference Bundle) bằng cách kết hợp dữ liệu lịch sử CSV cục bộ và dữ liệu giá streaming thời gian thực từ Kafka (đã được Spark ghi và đồng bộ lên MinIO Data Lake dưới dạng Parquet). Đây là cốt lõi của khâu tích hợp Lambda Architecture trong hệ thống.
* **Chức năng chính:**
  - Kết nối với MinIO Object Storage, tải các file Parquet chứa các bản tin giao dịch chứng khoán realtime mới nhất.
  - Trích xuất mức giá mới nhất của từng ticker và hợp nhất (merge) đè lên chuỗi dữ liệu lịch sử cục bộ.
  - Tính toán lại toàn bộ đặc trưng kỹ thuật, thực hiện chuẩn hóa động `RollingMinMaxScaler` và sinh đồ thị tương quan.
  - Lưu trữ tệp đầu vào `.npz` hoàn chỉnh tích hợp luồng streaming.
* **Cách thực hiện:**
  - **Hàm `create_s3_client()`:** Khởi tạo S3 Client kết nối đến dịch vụ MinIO.
  - **Hàm `list_and_download_parquet_files()`:** Quét bucket và tải đệ quy các tệp Parquet tạm thời về thư mục cục bộ, ghép (concatenate) chúng thành một DataFrame duy nhất.
  - **Hàm `latest_ticks_from_parquet()`:** Lọc ra bản tin có thời gian (`event_time`) và chỉ mục (`kafka_offset`) lớn nhất cho từng mã cổ phiếu để tìm ra mức giá giao dịch cuối cùng khớp lệnh.
  - **Hàm `merge_kafka_tick_into_history()`:** So sánh ngày của bản tin Kafka với ngày cuối cùng của dữ liệu lịch sử. Nếu trùng ngày, ghi đè giá Close/Open/High/Low bằng giá Kafka. Nếu là ngày mới, chèn thêm một dòng dữ liệu mới vào cuối DataFrame lịch sử.
  - **Đóng gói Bundle:** Sau khi ghép giá realtime, script chạy lại quy trình tính đặc trưng kỹ thuật, scale trượt, tạo đồ thị tương quan và ghi gói dữ liệu nén `.npz` (có bổ sung meta MinIO) ra đĩa.

### `D:/ie212/scripts/run_checkpoint_inference.py`
* **Mô tả:** Script suy luận (Inference Engine) chịu trách nhiệm nạp mô hình lai thích ứng từ file checkpoint và thực thi dự đoán trên bundle dữ liệu đầu vào.
* **Chức năng chính:**
  - Đọc tệp checkpoint `.pt` hoặc `.pth` và tự động suy luận kích thước các tầng mạng thần kinh.
  - Khởi tạo kiến trúc mô hình lai `HybridLSTMGNNGraphGate` khớp 100% với các thông số trích xuất.
  - Thực thi lan truyền xuôi (Forward Pass) với cơ chế cổng Graph Gate và xuất ra dự báo chênh lệch giá (Residual Price).
  - Tái cấu trúc bộ chuẩn hóa động `RollingMinMaxScaler` từ bundle đầu vào để đảo ngược chuẩn hóa giá đóng cửa về thang giá thực tế.
  - Tính toán tỷ suất sinh lời dự kiến (`pred_return`) và lưu kết quả chi tiết ra file JSON.
* **Cách thực hiện:**
  - **Hàm `load_checkpoint_generic()`:** Nạp an toàn tệp checkpoint lên CPU (tránh lỗi xung đột phần cứng) và bóc tách các khóa dữ liệu.
  - **Hàm `infer_model_dims_from_state_dict()`:** Phân tích cấu trúc các chiều Tensor để tự động tính ra `seq_input_dim`, `lstm_hidden` (chia 4 từ trọng số cổng LSTM), `node_input_dim`, `gnn_hidden` và `mlp_hidden`.
  - **Thực thi dự đoán:** Chuyển các tensor đầu vào (`X_seq`, `X_node`, `A`, `last_close`) qua mô hình với cờ `return_gate=True` để đồng thời lấy về mảng dự báo và giá trị cổng Graph Gate cho từng cổ phiếu.
  - **Đảo ngược chuẩn hóa:** Khôi phục tham số `RollingMinMaxScaler` từ bundle đầu vào, nhân ngược giá trị dự báo và giá cuối phiên về khoảng giá gốc, tính toán tỷ lệ phần trăm thay đổi giá (`pred_return = (pred_close - last_close) / last_close`) và xuất bản ghi JSON.

### `D:/ie212/scripts/save_inference_to_postgres.py`
* **Mô tả:** Tác vụ Ingest chịu trách nhiệm lưu trữ có cấu trúc kết quả dự báo từ file JSON vào PostgreSQL.
* **Chức năng chính:**
  - Tạo schema, thiết lập bảng `stock.inference_predictions` và cấu hình các chỉ mục (indexes).
  - Chèn toàn bộ thông tin dự báo của các mã chứng khoán kèm theo siêu dữ liệu chạy (Run ID, Checkpoint, Thiết bị chạy).
  - Sử dụng cơ chế ghi đè thông minh tránh trùng lặp dữ liệu giao dịch.
* **Cách thực hiện:**
  - **Hàm `ensure_table()`:** Thực thi SQL tạo schema `stock` và bảng `inference_predictions`. Cấu hình ràng buộc duy nhất `UNIQUE(prediction_run_id, ticker)` và đánh chỉ mục trên các trường `created_at`, `ticker` để tối ưu hóa truy vấn hiển thị ở FastAPI Dashboard.
  - **Ghi dữ liệu (Upsert):** Script đọc file JSON kết quả, phát sinh khóa chạy `prediction_run_id` tự động theo định dạng thời gian thực (nếu không được chỉ định). Sau đó chạy câu lệnh `INSERT INTO ... ON CONFLICT (prediction_run_id, ticker) DO UPDATE SET ...` để cập nhật đè dữ liệu mới nếu trùng lặp khóa.

### `D:/ie212/scripts/run_experiment.py`
* **Mô tả:** Kịch bản thực thi thí nghiệm Expanding Window (Expanding Window Backtest) quy mô lớn trên toàn bộ lịch sử dữ liệu để huấn luyện, kiểm thử và so sánh hiệu năng các mô hình.
* **Chức năng chính:**
  - Đồng bộ thiết lập hạt giống ngẫu nhiên (RNG Seeding) để đảm bảo tính tái lập của thí nghiệm.
  - Chạy mô hình Linear Regression làm baseline đối chứng.
  - Chạy liên tiếp các chu kỳ huấn luyện và kiểm thử mở rộng cho mô hình LSTM-Only và Hybrid LSTM-GNN Gated qua từng bước dịch chuyển thời gian.
  - Đo lường và lưu trữ toàn bộ các chỉ số lỗi Machine Learning, kết quả backtest danh mục đầu tư tài chính, ma trận đồ thị liên ngành và mức độ đóng mở cổng Graph Gate.
  - Đăng ký và lưu trữ checkpoint tối ưu nhất của các mô hình.
* **Cách thực hiện:**
  - **Hàm `seed_everything()`:** Đồng bộ seed trên `random`, `numpy`, `torch` và khóa cứng cấu hình cuDNN deterministic.
  - **Hàm `run_expanding_linear_backtest()`:** Trượt qua từng ngày kiểm thử, huấn luyện nhanh mô hình Linear Regression trên mảng đặc trưng phẳng và dự đoán giá đóng cửa.
  - **Hàm `run_joint_expanding_lstm_hybrid_backtest()`:** Duyệt qua các bước thời gian:
    - Sử dụng `prepare_expanding_step_data` trích xuất tập train/val/test và xây dựng đồ thị tương quan tương ứng.
    - Huấn luyện mô hình LSTM và mô hình lai Hybrid trên GPU/CPU. Áp dụng cơ chế nạp ấm (`Warm-Start`) truyền trọng số của bước trước sang bước sau để đẩy nhanh tốc độ hội tụ.
    - Ghi nhận lỗi MSE hàng ngày, thống kê số lượng cạnh đồ thị và phân phối trọng số của Graph Gate.
  - **Tổng hợp kết quả:** Xuất 5 tệp tin CSV chi tiết báo cáo so sánh kết quả từng bước chạy, lỗi trên từng cổ phiếu, thuộc tính đồ thị, thuộc tính cổng và lưu checkpoint của các mô hình tốt nhất vào thư mục `models/`.

### `D:/ie212/scripts/run_train.py`
* **Mô tả:** Kịch bản khởi tạo hoặc làm mới dữ liệu nguồn (Data Preparation & Warm Start Utility) trước khi chạy huấn luyện/thí nghiệm thực tế.
* **Chức năng chính:** Tải dữ liệu lịch sử mới nhất của các mã cổ phiếu, tiền xử lý đặc trưng kỹ thuật cơ bản, đồng bộ hóa trục ngày giao dịch chung và ghi đè lưu trữ làm giàu tài nguyên.
* **Cách thực hiện:** Hàm `main()` gọi lớp `load_all_tickers` từ `src.data_loader` để tải dữ liệu lịch sử yfinance từ khoảng năm 2005 đến nay (có hỗ trợ cờ `--refresh` để ép tải mới thay vì dùng cache CSV). Tiếp theo, gọi `align_common_index` loại bỏ các ngày lệch pha, tạo thư mục `data/raw` nếu chưa có và xuất 10 tệp CSV đồng bộ cho từng mã cổ phiếu, cuối cùng khởi tạo ma trận tensor và in kích thước kiểm chứng cấu trúc.

### `D:/ie212/scripts/test_expanding_data.py`
* **Mô tả:** Script kiểm thử đơn vị (Unit Test) nhằm xác minh tính đúng đắn của giải thuật cắt lát dữ liệu Expanding Window.
* **Chức năng chính:** Kiểm tra kích thước hình dạng (shape) và cấu trúc của các mảng dữ liệu sau khi thực hiện chuẩn hóa và đóng gói.
* **Cách thực hiện:** Script tải dữ liệu lịch sử thực tế, thực hiện fit/scale MinMaxScaler ban đầu, khởi tạo ma trận kề đơn vị và chạy hàm đóng gói dữ liệu `build_samples_for_target_range` trên toàn bộ tập huấn luyện để kiểm chứng xem kích thước chiều của tensor `X_seq`, `X_node`, `y_res` có trùng khớp hoàn toàn với thiết kế toán học đầu vào của PyTorch hay không.

### `D:/ie212/scripts/test_graph_builder.py`
* **Mô tả:** Script kiểm thử đơn vị giúp giám định chất lượng của engine xây dựng đồ thị tương quan.
* **Chức năng chính:** Kiểm nghiệm kích thước ma trận kề và chất lượng các mối quan hệ liên ngành được thiết lập trong cửa sổ huấn luyện đầu tiên.
* **Cách thực hiện:** Thiết lập phạm vi ngày huấn luyện tương ứng với cấu hình ban đầu (504 ngày giao dịch). Chạy hàm `build_combined_graph_from_train_window` để tạo ma trận kề hỗn hợp từ Pearson và Association Rules. Thực hiện in báo cáo thông tin gỡ lỗi, in mẫu ma trận kề thô và ma trận kề chuẩn hóa kích thước $5 \times 5$ lên màn hình console để kỹ sư kiểm tra trực quan.

### `D:/ie212/scripts/test_load_checkpoint.py`
* **Mô tả:** Script kiểm thử đơn vị quy trình khôi phục trạng thái mô hình từ file cứng.
* **Chức năng chính:** Đảm bảo hệ thống có thể đọc thành công các tệp tin checkpoint lưu trữ trọng số và nạp khớp hoàn toàn vào cấu trúc mạng thần kinh.
* **Cách thực hiện:** Khởi tạo thực thể trống của hai lớp mô hình `LSTMOnlyModel` và `HybridLSTMGNNGraphGate` từ cấu hình chuẩn. Thực hiện gọi hàm nạp `load_model_checkpoint` từ tệp checkpoint thực tế nằm trong thư mục `models/` và in ra metadata bổ trợ của tệp để xác nhận quá trình nạp thành công mà không phát sinh lỗi lệch pha tham số (parameter mismatch).

### `D:/ie212/scripts/test_model_forward.py`
* **Mô tả:** Script kiểm thử đơn vị xác minh tính thông suốt của luồng truyền dẫn xuôi (Forward Propagation) trong mạng thần kinh.
* **Chức năng chính:** Kiểm tra xem các lớp tích chập đồ thị, mạng LSTM và cổng Graph Gate có hoạt động đồng bộ không khi có dữ liệu truyền qua.
* **Cách thực hiện:** Sử dụng các thư viện toán học sinh ngẫu nhiên các tensor giả lập có kích thước chuẩn tương đương với một batch dữ liệu thực tế (Batch size = 2, Số cổ phiếu = 10, Trailing Days = 20, Features = 1). Truyền các tensor này qua mạng thần kinh LSTM và mạng lai để kiểm chứng xem tensor đầu ra có trả về đúng chiều thiết kế hay không, đồng thời xác nhận cổng Graph Gate sinh đủ trọng số cổng tương ứng cho từng node.

### `D:/ie212/scripts/test_prepare_step.py`
* **Mô tả:** Script kiểm thử tích hợp (Integration Test) kiểm nghiệm toàn bộ quy trình chuẩn bị dữ liệu tại một bước dịch chuyển đơn lẻ của cửa sổ mở rộng.
* **Chức năng chính:** Xác minh tính chính xác trong khâu phân chia tập dữ liệu huấn luyện, kiểm định và kiểm thử thực tế.
* **Cách thực hiện:** Tải dữ liệu, tính toán đặc trưng, scale và chạy hàm `prepare_expanding_step_data` tại vị trí chỉ mục bắt đầu kiểm thử. In ra màn hình ngày kiểm thử thực tế, cấu trúc ma trận kề của ngày hôm đó và kích thước chi tiết của ba gói dữ liệu đầu ra (Train pack, Val pack, Test pack) để bảo đảm không xảy ra lỗi tràn chỉ mục hoặc rò rỉ dữ liệu chuỗi thời gian.

### `D:/ie212/scripts/__init__.py`
* **Mô tả:** File khai báo thư mục `scripts/` là một package hợp lệ của Python.

---

---

## 🗄️ 4. Thư mục `airflow/dags/` (Điều phối quy trình tác vụ)

### `D:/ie212/airflow/dags/ie212_settings.py`
* **Mô tả:** Module cấu hình trung tâm (Airflow Settings Bootstrap) dành riêng cho môi trường chạy của các DAG Airflow. Nó quản lý, thống nhất và cung cấp các tham số kết nối dịch vụ trong mạng nội bộ Docker Network mà không cần viết lặp lại ở từng DAG.
* **Chức năng chính:**
  - Định nghĩa hàm tiện ích lấy cấu hình môi trường an toàn.
  - Cung cấp kết nối trực tiếp đến PostgreSQL từ các worker Airflow.
  - Đóng gói toàn bộ các hằng số mạng (Postgres, Kafka, Spark, MinIO, Docker Containers) thành từ điển `airflow_runtime_env` để các tác vụ Bash/Python sử dụng đồng bộ.
* **Cách thực hiện:**
  - **Hàm `env()`:** Nhận `name`, `default` và cờ `required`. Trích xuất biến hệ thống thông qua `os.getenv`. Nếu cờ `required` bật mà giá trị rỗng, lập tức ném lỗi `RuntimeError`.
  - **Hàm `get_pg_conn()`:** Trả về kết nối mở qua thư viện `psycopg2` đến cơ sở dữ liệu dựa trên các biến môi trường cấu hình: Host (`postgres`), Port (`5432`), DB (`stock_project`), User (`stock_user`), Password (`change_me_postgres`).
  - **Hàm `airflow_runtime_env()`:** Khởi tạo dictionary chứa 27 tham số cấu hình tĩnh mặc định thiết lập riêng cho hạ tầng mạng Docker Compose. Nó lướt qua toàn bộ keys và gọi hàm `env(k, v)` để tự động ghi đè bằng các biến môi trường thực tế nếu được cấu hình trên Airflow Worker.

### `D:/ie212/airflow/dags/ie212_smoke_test.py`
* **Mô tả:** DAG chạy thử nghiệm tối giản (Sanity Smoke Test) dùng để kiểm chứng xem Airflow Scheduler và các Worker đang hoạt động bình thường hay gặp sự cố tắc nghẽn hàng chờ.
* **Chức năng chính:** Chạy thử nghiệm chuỗi 2 tác vụ Python in thông báo đơn giản mà không tương tác với bất kỳ cơ sở dữ liệu hay hạ tầng mạng bên ngoài nào.
* **Cách thực hiện:**
  - Sử dụng TaskFlow API định nghĩa DAG với các decorator `@dag` và `@task`. Thiết lập lịch chạy thủ công `schedule=None` để kiểm nghiệm theo yêu cầu.
  - **Tác vụ `smoke_test_run()`:** Trả về chuỗi ký tự đơn giản `"ok"`.
  - **Tác vụ `smoke_test_verify()`:** Nhận đầu vào là kết quả của tác vụ trước, in ra màn hình nhật ký (log) thông báo `"Smoke test verification passed. Pipeline status: ok"`. Thiết lập mối liên kết phụ thuộc thông qua lời gọi hàm lồng nhau trực quan: `smoke_test_verify(smoke_test_run())`.

### `D:/ie212/airflow/dags/ie212_full_validation_pipeline.py`
* **Mô tả:** DAG giám sát hệ thống toàn diện (System Health Auditor DAG). Nó thực hiện quét và kiểm định định kỳ chất lượng kết nối và tính sẵn sàng của tất cả các dịch vụ hạ tầng trong hệ thống trước khi các pipeline xử lý dữ liệu phức tạp chạy.
* **Chức năng chính:**
  - Tự động chuẩn bị bảng ghi log audit trong PostgreSQL.
  - Kiểm tra kết nối socket tới Kafka (port 9092) và Spark Master (port 8080).
  - Kiểm tra tình trạng hoạt động và live endpoint của Object Storage MinIO.
  - Kiểm định Postgres: Đếm số bản ghi trong bảng batch của Kafka và phát hiện nếu thiếu bất kỳ bảng bắt buộc nào (`predictions`, `model_registry`, v.v.).
  - Ghi báo cáo kiểm thử vào PostgreSQL và kích hoạt lỗi DAG nếu bất kỳ dịch vụ nào ngoại tuyến.
* **Cách thực hiện:**
  - **Tác vụ `ensure_audit_table`:** Tạo schema `stock` và bảng `stock.pipeline_audit` lưu vết lịch sử kiểm định (ngày giờ, trạng thái từng dịch vụ, lỗi cụ thể).
  - **Tác vụ `check_kafka`:** Dùng `socket.create_connection(("kafka", 9092), timeout=5)` kiểm tra xem broker có lắng nghe không.
  - **Tác vụ `check_spark_master`:** Dùng thư viện `urllib.request` gửi yêu cầu HTTP GET đến `http://spark-master:8080`, đảm bảo mã phản hồi trả về là `200`.
  - **Tác vụ `check_minio`:** Gửi yêu cầu HTTP GET đến cổng sức khỏe của MinIO `http://minio:9000/minio/health/live`, kiểm tra mã 200 và body trả về chứa `"OK"`.
  - **Tác vụ `check_postgres`:** Tạo kết nối DB, truy vấn danh sách bảng hiện hữu trong schema `stock`. So khớp với tập hợp các bảng bắt buộc để tìm ra bảng bị thiếu. Đồng thời đếm số lượng dòng trong `stock.kafka_ticks_batch`.
  - **Tác vụ `write_audit`:** Dùng `XCom` thu thập kết quả kiểm thử từ 4 tác vụ trước, tổng hợp danh sách lỗi và thực thi câu lệnh SQL INSERT ghi toàn bộ bản ghi audit vào bảng `stock.pipeline_audit`.
  - **Tác vụ `validate_pipeline`:** Tổng hợp lỗi qua XCom. Nếu có bất kỳ lỗi kết nối nào hoặc bảng dữ liệu Kafka Batch bị trống (`count <= 0`), nó sẽ ném ngoại lệ `ValueError` làm thất bại hoàn toàn luồng chạy của DAG để cảnh báo kỹ sư.

### `D:/ie212/airflow/dags/ie212_data_pipeline.py`
* **Mô tả:** DAG kiểm định chất lượng luồng dữ liệu Batch (Batch Data Path Validator DAG). Nó thực hiện một phiên bản kiểm định rút gọn, tập trung chủ yếu vào sự kết nối của cụm Big Data và sự toàn vẹn của bảng lưu trữ Kafka Batch.
* **Chức năng chính:** Kiểm tra khả năng hoạt động của Kafka, Spark Master, MinIO, PostgreSQL và đếm bản ghi trong bảng dữ liệu thô đã được nạp qua Spark Batch.
* **Cách thực hiện:** Kịch bản import và tái sử dụng trực tiếp các hàm logic từ `ie212_full_validation_pipeline.py` như `ensure_audit_table`, `check_kafka`, `check_spark_master`, `check_minio`, `check_postgres`, `write_audit`, `validate_pipeline`. Nó thiết lập cấu hình DAG chạy độc lập mang tên `ie212_data_pipeline` và liên kết các task qua toán tử bitwise `t1 >> [t2, t3, t4, t5] >> t6 >> t7`.

### `D:/ie212/airflow/dags/ie212_spark_exec_pipeline.py`
* **Mô tả:** DAG điều phối quy trình trích xuất và đồng bộ dữ liệu quy mô lớn (Spark Execution & Data Sync DAG). Nó thực thi công việc xử lý dữ liệu Batch của Speed Layer và di chuyển dữ liệu thô vào Data Lake MinIO.
* **Chức năng chính:**
  - Ghi log audit ban đầu.
  - Sử dụng Spark Submit đẩy tác vụ đọc dữ liệu Kafka đổ vào PostgreSQL.
  - Sử dụng Spark Submit đẩy tác vụ xuất dữ liệu Kafka ra tệp Parquet phân mảnh cục bộ trên ổ đĩa chung.
  - Kiểm tra xem file Parquet đã được tạo đầy đủ chưa.
  - Điều khiển Docker container của MinIO Client (`mc`) đồng bộ hóa (upload) toàn bộ tệp Parquet cục bộ lên MinIO Object Storage đám mây.
* **Cách thực hiện:**
  - Cấu hình dictionary `env_vars` bằng cách gọi `airflow_runtime_env()`.
  - **Tác vụ `spark_kafka_to_postgres`:** Dùng `BashOperator` thực thi lệnh `docker exec` đẩy tác vụ spark-submit vào container Spark Master. Lệnh chạy job `write_kafka_batch_to_postgres.py` kèm tham số `--packages` kết nối Kafka và Postgres JDBC Driver.
  - **Tác vụ `spark_kafka_to_parquet`:** Tương tự, dùng `BashOperator` kích hoạt tác vụ chạy job `write_kafka_batch_to_parquet.py` để xuất dữ liệu ra thư mục Parquet chung đặt tại `/opt/airflow/shared/spark_out/kafka_ticks_parquet`.
  - **Tác vụ `validate_parquet_output`:** Dùng `PythonOperator` quét thư mục Parquet cục bộ bằng `Path.glob()`. Nếu không tìm thấy tệp Parquet hợp lệ hoặc dung lượng rỗng, lập tức ném lỗi dừng pipeline.
  - **Tác vụ `sync_parquet_to_minio`:** Sử dụng `BashOperator` điều khiển container MinIO Client chạy lệnh CLI: cấu hình alias kết nối MinIO local → tạo bucket processed → chạy lệnh đồng bộ `mc mirror --overwrite` đẩy toàn bộ tệp Parquet từ thư mục chung lên bucket `processed` theo prefix `kafka_ticks_parquet`.

### `D:/ie212/airflow/dags/ie212_end_to_end_inference_pipeline.py`
* **Mô tả:** DAG điều phối suy luận AI tự động (AI Inference Pipeline DAG). Nó đóng vai trò tự động hóa chuỗi quy trình nạp dữ liệu lịch sử cục bộ, thực thi mô hình lai thích ứng và lưu trữ kết quả dự báo.
* **Chức năng chính:**
  - Kích hoạt tiến trình tiền xử lý đóng gói bundle NumPy mới nhất.
  - Thực thi lan truyền xuôi mô hình học máy PyTorch trên container ML riêng biệt để thu về dự báo.
  - Nạp toàn bộ kết quả dự báo vào PostgreSQL.
  - Thực thi truy vấn PostgreSQL để đảm bảo dữ liệu dự báo đã ghi nhận thành công.
* **Cách thực hiện:**
  - Cấu hình các biến môi trường thông qua `airflow_runtime_env()`.
  - **Tác vụ `build_inference_bundle`:** Dùng `BashOperator` chạy lệnh `docker exec ie212-ml-infer python scripts/build_latest_inference_bundle.py` bên trong container ML. Đầu ra là file `.npz` nén.
  - **Tác vụ `run_pytorch_inference`:** Sử dụng `BashOperator` kích hoạt `docker exec ie212-ml-infer python scripts/run_checkpoint_inference.py --checkpoint ... --input-npz ...` chạy suy luận, lưu kết quả JSON ra thư mục output.
  - **Tác vụ `save_predictions_to_postgres`:** Dùng `BashOperator` chạy lệnh `docker exec ie212-ml-infer python scripts/save_inference_to_postgres.py --input-json ...` để phân tách JSON và INSERT ghi đè vào PostgreSQL.
  - **Tác vụ `validate_inference_predictions`:** Sử dụng `PythonOperator` kết nối PostgreSQL, thực hiện đếm số dòng dữ liệu có `prediction_run_id` tương ứng trong bảng `stock.inference_predictions`. Nếu số lượng dòng bằng 0 hoặc bảng không tồn tại, lập tức báo lỗi DAG.

### `D:/ie212/airflow/dags/ie212_inference_ingest_pipeline.py`
* **Mô tả:** DAG nạp kết quả dự đoán (Inference Ingestion DAG). Đây là một quy trình kiểm thử hoặc chạy nhanh khi người dùng đã chạy suy luận thủ công từ trước và chỉ cần nạp dữ liệu JSON thô có sẵn vào cơ sở dữ liệu.
* **Chức năng chính:** Chạy script nạp tệp JSON tĩnh dự phòng vào bảng PostgreSQL và xác minh tính toàn vẹn dữ liệu trong bảng dự báo.
* **Cách thực hiện:** Kịch bản chỉ gồm 2 tác vụ cơ bản được import từ `ie212_end_to_end_inference_pipeline.py`: task `save_predictions_to_postgres` (sử dụng `BashOperator` nạp file cấu hình tĩnh `/workspace/outputs/inference/latest_prediction.json`) liên kết trực tiếp đến task `validate_inference_predictions` để kiểm tra số lượng bản ghi sau khi nạp.

### `D:/ie212/airflow/dags/ie212_kafka_end_to_end_smoke_test.py`
* **Mô tả:** DAG kiểm định tích hợp luồng Streaming (Streaming End-to-End Smoke Test DAG). Nó giả lập một phiên hoạt động hoàn chỉnh từ khâu sản xuất dữ liệu thời gian thực đến khâu lưu trữ.
* **Chức năng chính:**
  - Tự động chạy Kafka Producer giả lập phát duy nhất 1 vòng dữ liệu.
  - Khởi chạy tác vụ Spark Submit đọc dữ liệu Kafka đó và ghi đồng bộ vào Postgres.
  - Kiểm tra xem dữ liệu giả lập đã nằm trong cơ sở dữ liệu Postgres chưa.
* **Cách thực hiện:**
  - **Tác vụ `produce_kafka_ticks`:** Dùng `BashOperator` chạy docker exec kích hoạt producer `publish_stock_ticks.py` với cấu hình `--max-iterations 1 --source csv` để gửi 1 đợt giá giả lập từ file CSV thô vào Kafka topic.
  - **Tác vụ `spark_write_kafka_batch_to_postgres`:** Dùng `BashOperator` gửi lệnh Spark Submit thực thi job Spark `write_kafka_batch_to_postgres.py` tiêu thụ và ghi lô dữ liệu đó xuống Postgres.
  - **Tác vụ `validate_kafka_batch_table`:** Sử dụng `PythonOperator` chạy truy vấn Postgres đếm số lượng dòng trong bảng `stock.kafka_ticks_batch` để bảo đảm dữ liệu từ Kafka đã cập bến an toàn.

### `D:/ie212/airflow/dags/ie212_kafka_to_inference_pipeline.py`
* **Mô tả:** Siêu DAG điều phối thời gian thực (Real-time Master Lambda Pipeline DAG). Đây là quy trình phức tạp nhất thể hiện sự phối hợp nhịp nhàng giữa Speed Layer, Batch Layer và Serving Layer của hệ thống Big Data.
* **Chức năng chính:** Điều phối tuần tự chuỗi 7 bước: Sinh dữ liệu Kafka realtime → Spark ghi Postgres & Parquet cục bộ → Đồng bộ Parquet lên MinIO Data Lake → Tải Parquet từ MinIO tạo bundle dự báo tích hợp realtime → Chạy dự báo mô hình PyTorch Hybrid → Lưu dự báo vào Postgres → Chạy kiểm định chất lượng toàn bộ dữ liệu cuối kỳ.
* **Cách thực hiện:**
  - Tích hợp và liên kết các task từ các pipeline thành phần:
    1. **`produce_kafka_ticks`** (Sinh dữ liệu Kafka).
    2. **`spark_kafka_to_postgres`** và **`spark_kafka_to_parquet`** chạy song song (Spark ghi dữ liệu Postgres/Parquet).
    3. **`sync_parquet_to_minio`** (Đẩy Parquet lên MinIO Bucket).
    4. **`build_kafka_inference_bundle`** (Dùng `BashOperator` chạy script `build_kafka_inference_bundle.py` bên trong container ML, tự động kết nối MinIO tải các file Parquet realtime vừa đồng bộ để ghép với lịch sử CSV cục bộ và xuất file `.npz`).
    5. **`run_pytorch_inference`** (Chạy suy luận mô hình lai Hybrid trên bundle vừa tạo).
    6. **`save_predictions_to_postgres`** (Lưu kết quả dự đoán vào DB).
    7. **`validate_pipeline_outputs`** (Kiểm tra xem số dòng dự báo và số dòng batch Kafka trên Postgres đều lớn hơn 0).

### `D:/ie212/airflow/dags/ie212_retrain_pipeline.py`
* **Mô tả:** DAG tự động tái huấn luyện mô hình (Continuous Training - CT Pipeline DAG). Nó đóng vai trò là "bộ não tự thích ứng" của Serving Layer, giúp mô hình luôn học hỏi và cập nhật theo xu hướng mới nhất của thị trường chứng khoán.
* **Chức năng chính:**
  - Kiểm tra xem lượng dữ liệu mới tích lũy đã đủ lớn để kích hoạt quá trình tái huấn luyện hay chưa (Concept Drift Detector).
  - Tải dữ liệu lịch sử yfinance mới nhất và đồng bộ lên MinIO Object Storage đám mây để lưu trữ.
  - Triển khai tiến trình huấn luyện offline mô hình lai LSTM-GNN Gated trên container ML để tìm checkpoint tốt nhất.
  - Đồng bộ checkpoint mới huấn luyện lên MinIO Model Lake và đăng ký phiên bản mới vào PostgreSQL Model Registry.
* **Cách thực hiện:**
  - **Tác vụ `check_retrain_trigger`:** Dùng `PythonOperator` kết nối PostgreSQL, truy vấn ngày cập nhật gần nhất của mô hình trong `stock.model_registry` và ngày lớn nhất của dữ liệu thô. Nếu khoảng cách ngày nhỏ hơn cấu hình `RETRAIN_MIN_NEW_DAYS` (mặc định 20 ngày), task sẽ ném lỗi `AirflowSkipException` tự động bỏ qua toàn bộ các bước huấn luyện phía sau để tiết kiệm tài nguyên.
  - **Tác vụ `download_and_sync_raw_data`:** Dùng `BashOperator` chạy docker exec kích hoạt script `run_train.py --refresh` kéo dữ liệu yfinance mới nhất ghi đè vào CSV. Tiếp theo gọi script `sync_parquet_to_minio.py` tải các CSV thô đó lên MinIO làm phiên bản dữ liệu lưu trữ (Data Versioning).
  - **Tác vụ `run_offline_retraining`:** Dùng `BashOperator` chạy docker exec kích hoạt `run_experiment.py` thực hiện huấn luyện Expanding Window lại từ đầu trên dữ liệu mới để tìm bộ trọng số tối ưu.
  - **Tác vụ `register_new_model`:** Dùng `BashOperator` chạy script `save_inference_to_postgres.py` đăng ký siêu dữ liệu của checkpoint vừa tạo (Run ID, MSE, Sharpe, đường dẫn MinIO) vào bảng `stock.model_registry` phục vụ cho khâu quản lý phiên bản mô hình (Model Versioning).
  - **Tác vụ `sync_checkpoint_to_minio`:** Sử dụng CLI `mc mirror` tải tệp checkpoint `.pt` mới nhất từ thư mục local lên MinIO bucket `models` để các container suy luận khác có thể kéo về sử dụng.

---

## 🌐 5. Thư mục `services/` (Các dịch vụ API & Spark Jobs)

### `D:/ie212/services/__init__.py`
* **Mô tả:** Tệp khởi tạo trống đóng vai trò khai báo thư mục `services/` là một package Python hợp lệ.

### 🌐 5.1. Dịch vụ API (`services/api/`)

#### `D:/ie212/services/api/__init__.py`
* **Mô tả:** Tệp khởi tạo trống đóng vai trò khai báo thư mục con `services/api/` là một package Python hợp lệ.

#### `D:/ie212/services/api/main.py`
* **Mô tả:** Máy chủ API chính (Core API Server) của Serving Layer, chịu trách nhiệm cung cấp dữ liệu dự báo, xu hướng lịch sử, luồng giá thời gian thực (Streaming) và phân tích đầu tư AI cho ứng dụng giao diện Dashboard.
* **Chức năng chính:**
  - Định nghĩa cấu trúc dữ liệu đầu ra an toàn thông qua Pydantic.
  - Phục vụ giao diện Web Dashboard tĩnh và quản lý cấu hình CORS cho phép gọi API từ xa.
  - Cung cấp các Endpoint GET truy vấn dữ liệu dự báo lịch sử, danh sách mô hình và danh mục cổ phiếu từ PostgreSQL.
  - Triển khai fallback đọc file CSV cục bộ nếu DB lỗi để đảm bảo hệ thống luôn hiển thị dữ liệu lịch sử.
  - Tích hợp luồng Server-Sent Events (SSE) và WebSocket truyền dữ liệu giá thời gian thực từ `runtime_stream_service.py`.
  - Kết nối Endpoint tư vấn AI gọi đến dịch vụ phân tích LLM.
* **Cách thực hiện:**
  - Khởi tạo FastAPI app. Cấu hình CORS middleware cho phép tất cả các nguồn (`*`).
  - Sử dụng `NoCacheStaticFiles` thừa kế từ `StaticFiles` để phục vụ các file giao diện tĩnh (`/dashboard` trỏ về `frontend/dist`), ghi đè headers `Cache-Control: no-store, must-revalidate` để trình duyệt luôn tải giao diện mới nhất khi có thay đổi.
  - Sử dụng các Pydantic model (`PredictionItem`, `RunSummary`, `SystemStatus`) để kiểm tra kiểu dữ liệu đầu ra nghiêm ngặt.
  - **Endpoint `/predictions/latest`:** Kết nối PostgreSQL qua `psycopg2`, thực thi câu lệnh SQL tìm Run ID gần nhất, lấy toàn bộ bản ghi dự báo giá đóng cửa, tỷ suất sinh lời và trọng số cổng Graph Gate của 10 mã cổ phiếu.
  - **Endpoint `/stream/prices`:** Trả về một `StreamingResponse` kiểu Event-Stream (`text/event-stream`). Nó liên tục đọc mảng giá cập nhật từ `DemoStreamEngine.get_latest()` mỗi 1 giây và đẩy xuống cho Client dưới dạng JSON SSE.
  - **Endpoint `/ai/analyze`:** Tiếp nhận yêu cầu phân tích mã cổ phiếu từ giao diện, gọi hàm `analyze_ticker_with_llm()` từ module AI và trả về báo cáo khuyến nghị.

#### `D:/ie212/services/api/main_backup.py`
* **Mô tả:** Tệp API dự phòng (v1.1.0 Legacy API Backup). Đây là phiên bản API đơn giản đời đầu được giữ lại để kiểm thử tính tương thích hoặc sử dụng làm backup khi server chính FastAPI gặp sự cố nghiêm trọng.
* **Chức năng chính:** Cung cấp các Endpoint cơ bản để truy vấn thông số sức khỏe và danh sách Run ID dự báo thô trong DB.
* **Cách thực hiện:** Khởi tạo FastAPI app tối giản. Sử dụng trực tiếp `psycopg2` để mở kết nối đến PostgreSQL và thực hiện các câu lệnh SELECT đơn giản trên bảng `stock.inference_predictions`. Phiên bản này không chứa các luồng SSE, WebSocket, fallback CSV, Gemini AI, hay cấu hình nén cache tĩnh như `main.py`.

#### `D:/ie212/services/api/runtime_stream_service.py`
* **Mô tả:** Động cơ giả lập luồng dữ liệu thời gian thực (`DemoStreamEngine`). Nó đóng vai trò tạo ra dòng giá cổ phiếu chạy liên tục trên giao diện Dashboard khi hệ thống chạy ở chế độ demo.
* **Chức năng chính:**
  - Nạp dữ liệu giá đóng cửa thực tế gần nhất làm mốc tham chiếu khởi điểm.
  - Sử dụng đa luồng (threading) chạy vòng lặp vô hạn để định kỳ cập nhật bước giá mới sau mỗi vài giây.
  - Tạo ra dao động giá ngẫu nhiên tự nhiên (như thị trường thật) nhưng có cơ chế bảo vệ chống lệch giá quá xa khỏi thực tế.
  - Tự động sinh tín hiệu kỹ thuật (BUY/SELL/HOLD) tương ứng với giá trị mô phỏng.
* **Cách thực hiện:**
  - Khởi tạo lớp `DemoStreamEngine` có luồng khóa an toàn `threading.Lock()` để tránh xung đột dữ liệu (Race Condition) khi nhiều API client gọi đọc/ghi cùng lúc.
  - Hàm `reload()` kết nối Postgres lấy giá thực tế cuối cùng lưu vào bộ nhớ cache RAM cục bộ.
  - Hàm `generate_point()` chạy ngầm: Mỗi chu kỳ $N$ giây, nó cộng thêm độ nhiễu ngẫu nhiên bằng `random.uniform(-0.0008, 0.0008)` nhân với giá trị Close hiện tại để sinh ra giá mới.
  - **Cơ chế chống lệch giá (`DRIFT_GUARD_PCT`):** Kiểm tra nếu giá mô phỏng lệch vượt quá 2% so với giá đóng cửa thực tế trong PostgreSQL, nó sẽ tự động điều chỉnh hướng sinh giá ngược lại để kéo giá về sát mốc thực tế, tránh bùng nổ sai số lớn sau thời gian chạy dài.
  - Lưu trữ lịch sử giao dịch mô phỏng giới hạn tối đa 200 điểm gần nhất trong mảng đệm.

#### `D:/ie212/services/api/ai_decision_service.py`
* **Mô tả:** Dịch vụ tư vấn đầu tư thông minh kết hợp mô hình AI Lai và Generative AI (Google Gemini). Nó phân tích các chỉ số định lượng của mô hình lai thích ứng cùng xu hướng thị trường để đưa ra khuyến nghị đầu tư bằng ngôn ngữ tự nhiên.
* **Chức năng chính:**
  - Truy vấn dữ liệu lịch sử giá 15 ngày qua và lấy thông tin dự báo mới nhất từ PostgreSQL.
  - Nạp các thông số đánh giá lỗi và hiệu năng backtest tài chính của mô hình lai.
  - Định hình cấu trúc Prompt và gửi yêu cầu phân tích chuyên sâu tới Google Gemini API.
  - Tự động chuyển đổi sang thuật toán phân tích định lượng bằng tiếng Việt (Fallback Rules) nếu không có internet hoặc thiếu Gemini API Key.
* **Cách thực hiện:**
  - Hàm `analyze_ticker_with_llm()`:
    1. Query PostgreSQL lấy giá thực và giá dự đoán mới nhất của mã cổ phiếu.
    2. Đọc file `evaluation_metrics.json` lấy các thông số: Win Rate, Sharpe Ratio, Max Drawdown, Directional Accuracy.
    3. Đọc DB lấy chuỗi giá đóng cửa lịch sử 15 ngày qua để tạo chuỗi xu hướng dạng: `$150.2, $152.1, ...`.
    4. Đọc file mẫu `services/api/PROMPT.md` chứa khung prompt phân tích tài chính có cấu trúc. Điền toàn bộ thông số và chuỗi lịch sử vào prompt mẫu.
    5. **Gọi Gemini API:** Hàm `call_gemini_api()` gửi request POST dạng JSON tới endpoint `gemini-1.5-flash` kèm API Key. Cấu hình `responseMimeType="application/json"` và `temperature=0.2` để Gemini bắt buộc trả về chuỗi JSON chứa 2 trường `reasons` và `risks`.
    6. **Fallback logic:** Nếu API Key trống hoặc gọi API lỗi, hệ thống kích hoạt bộ luật logic tài chính. Nó tự tính toán tín hiệu: `BUY` nếu tỷ suất tăng vượt 0.1%, `SELL` nếu giảm dưới -0.1%, ngược lại là `HOLD`. Tự động tạo ra các đoạn văn phân tích Tiếng Việt chi tiết (nêu rõ Sharpe, Max Drawdown, ảnh hưởng của Graph Gate và rủi ro) khớp chính xác với tình trạng tài sản.

---

### 🪵 5.2. Các tác vụ Spark (`services/spark/jobs/`)

#### `D:/ie212/services/spark/jobs/simple_spark_check.py`
* **Mô tả:** Tác vụ kiểm tra sức khỏe của cụm tính toán Apache Spark (Spark Cluster Sanity Check Job).
* **Chức năng chính:** Khởi tạo Spark Session và chạy thử nghiệm biến đổi trên DataFrame đơn giản để kiểm tra khả năng phân bổ tài nguyên trên Spark Master/Workers.
* **Cách thực hiện:** Hàm `main()` gọi `SparkSession.builder.appName("SimpleSparkCheck").getOrCreate()`. Nó tạo ra một tập dữ liệu giả lập chứa danh sách các ticker `["AAPL", "MSFT", "AMD"]`, chuyển đổi sang Spark DataFrame, in lược đồ ra console bằng `show()` và đếm số lượng phần tử nhằm kiểm tra sức khỏe Spark Master/Workers, sau đó tắt session.

#### `D:/ie212/services/spark/jobs/read_kafka_batch.py`
* **Mô tả:** Tác vụ Spark Batch đọc luồng Kafka (Kafka Batch Consumer Job). Nó được sử dụng để kiểm thử khâu kết nối và giải mã bản tin từ Kafka topic ở dạng lô dữ liệu.
* **Chức năng chính:** Kết nối với Kafka broker nội bộ, tải toàn bộ bản tin trong topic chứng khoán từ điểm bắt đầu (`earliest`) đến điểm kết thúc (`latest`) và hiển thị cấu trúc dữ liệu thô.
* **Cách thực hiện:** Sử dụng `spark.read` với định dạng `kafka`. Cấu hình máy chủ `kafka:9092` và topic `stock-price`. Bản tin thô nhận về dưới dạng nhị phân sẽ được ép kiểu cột `value` sang `StringType()`. Script áp dụng một cấu trúc schema định sẵn (`symbol` string, `price` double) để chuyển đổi chuỗi JSON thành các trường dữ liệu tương quan.

#### `D:/ie212/services/spark/jobs/read_kafka_stream.py`
* **Mô tả:** Tác vụ Spark Streaming đọc luồng Kafka liên tục (Kafka Real-time Console Stream Job). Nó dùng để kiểm tra tính liên tục của luồng truyền dẫn thời gian thực.
* **Chức năng chính:** Đăng ký nhận luồng dữ liệu realtime từ Kafka topic và in trực tiếp ra màn hình console của Spark Worker.
* **Cách thực hiện:** Sử dụng `spark.readStream` kết nối đến topic `stock-price` của Kafka. Chuyển đổi dữ liệu nhị phân JSON sang các cột tương ứng, sau đó gọi phương thức ghi luồng `writeStream` cấu hình định dạng xuất là `console`. Gọi `awaitTermination()` để giữ tiến trình chạy vô hạn theo dõi luồng.

#### `D:/ie212/services/spark/jobs/write_kafka_batch_to_postgres.py`
* **Mô tả:** Tác vụ nạp dữ liệu lô lớn từ Kafka vào cơ sở dữ liệu PostgreSQL (Kafka-Postgres JDBC Batch Sync Job) của Batch Layer.
* **Chức năng chính:** Trích xuất toàn bộ dữ liệu lịch sử trong Kafka topic dưới dạng lô, chuyển đổi sang bảng quan hệ và ghi đồng bộ xuống PostgreSQL bằng kết nối JDBC.
* **Cách thực hiện:**
  - Khởi tạo Spark Session nạp thêm gói phụ thuộc Kafka SQL package.
  - Đọc batch dữ liệu từ `earliest` đến `latest`.
  - Phân tích cú pháp cột JSON nhị phân, ép kiểu các cột: `symbol` thành String, `price` thành Double, `event_time` thành Timestamp, và giữ lại siêu dữ liệu của Kafka (`partition` và `offset`).
  - Lọc bỏ các dòng dữ liệu bị lỗi hoặc khuyết thiếu thông tin (`dropna`).
  - Ghi hàng loạt vào bảng `stock.kafka_ticks_batch` thông qua JDBC Driver PostgreSQL với cấu hình lưu trữ ghi đè (`Overwrite`).

#### `D:/ie212/services/spark/jobs/write_kafka_batch_to_parquet.py`
* **Mô tả:** Tác vụ xuất bản dữ liệu từ Kafka ra định dạng lưu trữ Parquet (Kafka-Parquet Storage Job) của Batch Layer, phục vụ lưu trữ dữ liệu nén hiệu năng cao lâu dài trên MinIO Data Lake.
* **Chức năng chính:** Đọc hàng loạt dữ liệu Kafka, trích xuất cấu trúc và ghi xuống ổ đĩa chung dưới dạng file Parquet nén.
* **Cách thực hiện:** Tải dữ liệu từ Kafka topic tương tự như job Postgres. Sau khi chuyển đổi kiểu dữ liệu thành công, script gọi hàm `.coalesce(1)` để dồn (merge) tất cả các mảnh phân vùng dữ liệu nhỏ lẻ trên các workers về duy nhất một tệp tin đầu ra thống nhất, sau đó thực hiện ghi đè nén Parquet xuống thư mục chung `/opt/spark/out/kafka_ticks_parquet`.

#### `D:/ie212/services/spark/jobs/write_kafka_stream_to_postgres.py`
* **Mô tả:** Tác vụ lưu trữ luồng dữ liệu thời gian thực từ Kafka vào PostgreSQL (Kafka-Postgres Real-time Structured Streaming Job) thuộc Speed Layer của hệ thống Big Data.
* **Chức năng chính:** Đăng ký nhận luồng dữ liệu realtime liên tục từ Kafka broker, định nghĩa hàm xử lý vi lô (micro-batch) để chèn đồng thời giá trị giao dịch vào PostgreSQL tức thời theo từng mili-giây.
* **Cách thực hiện:**
  - Sử dụng `spark.readStream` để liên tục tiêu thụ các bản tin mới nhất trong topic Kafka.
  - Phân tích cú pháp JSON và bổ sung thêm cột thời gian nạp thực tế bằng `current_timestamp()`.
  - Định nghĩa hàm callback `write_batch_to_postgres(df, epoch_id)`: Ở mỗi micro-batch dữ liệu mới xuất hiện, hàm này sử dụng JDBC Driver ghi trực tiếp DataFrame đó vào bảng PostgreSQL `stock.kafka_ticks`.
  - Gọi phương thức ghi luồng `writeStream`, thiết lập trigger thời gian hoặc cấu hình chạy liên tục, kích hoạt cơ chế `foreachBatch` trỏ đến hàm callback và khai báo thư mục lưu trữ Checkpoint `/opt/spark/work-dir/checkpoints/...` giúp đảm bảo khả năng phục hồi lỗi không mất dữ liệu.

---

## 🪵 6. Thư mục `frontend/` (Chứa các đoạn mã phụ trợ)

### `D:/ie212/frontend/node_modules/flatted/python/flatted.py`
* **Mô tả:** Đây là tệp Python đi kèm thư viện bên thứ ba `flatted`, nằm trong thư mục `node_modules` của Frontend. Mục đích của thư viện này là hỗ trợ mã hóa (`stringify`) và giải mã (`parse`) những cấu trúc dữ liệu phức tạp có tham chiếu vòng (Circular Reference), tức là một object/list có thể tham chiếu ngược lại chính nó hoặc tham chiếu chéo qua nhiều cấp. JSON chuẩn của Python (`json.dumps`) không xử lý được loại dữ liệu này, vì vậy `flatted.py` dùng cơ chế "làm phẳng" object thành một mảng tham chiếu để có thể lưu trữ hoặc truyền tải an toàn.
* **Chức năng chính:**
  - Cung cấp hàm `stringify(value, *args, **kwargs)` để chuyển object/list/dict có khả năng chứa tham chiếu lặp thành chuỗi JSON đặc biệt.
  - Cung cấp hàm `parse(value, *args, **kwargs)` để khôi phục chuỗi JSON dạng flatted trở lại object/list/dict ban đầu với các quan hệ tham chiếu được nối lại đúng vị trí.
  - Theo dõi các object đã gặp thông qua lớp `_Known`, tránh ghi lặp lại cùng một object nhiều lần.
  - Bọc các chuỗi bằng lớp `_String` trong quá trình parse để phân biệt chuỗi dữ liệu thật và chuỗi chỉ mục tham chiếu.
  - Hỗ trợ xử lý cả `list`, `tuple`, `dict` và `str` thông qua các hàm nhận diện kiểu dữ liệu nội bộ.
* **Cách thực hiện:**
  - **Lớp `_Known`:** Tạo hai danh sách song song `key` và `value`. `key` lưu object gốc đã gặp, còn `value` lưu chỉ mục dạng chuỗi tương ứng với object đó trong mảng đầu vào. Nhờ vậy, khi gặp lại cùng object, chương trình không ghi object lần nữa mà chỉ ghi chỉ mục tham chiếu.
  - **Lớp `_String`:** Bọc giá trị string trong giai đoạn `parse()` để tránh nhầm lẫn giữa string dữ liệu bình thường và string đại diện cho chỉ mục tham chiếu trong mảng flatted.
  - **Nhóm hàm kiểm tra kiểu:** `_is_array()`, `_is_object()`, `_is_string()` xác định một giá trị là danh sách/tuple, dictionary hay chuỗi. `_array_keys()` và `_object_keys()` tạo iterator duyệt key/index tương ứng cho list và dict.
  - **Hàm `_index()`:** Khi phát hiện một object/list/dict/string mới chưa từng xuất hiện, hàm này thêm nó vào mảng `input`, sinh chỉ mục mới bằng `len(input) - 1`, sau đó lưu mapping object → index vào `_Known`.
  - **Hàm `_relate()`:** Kiểm tra xem một giá trị đã từng xuất hiện chưa. Nếu có, trả về chỉ mục cũ. Nếu chưa, gọi `_index()` để đăng ký mới. Đây là bước quan trọng giúp xử lý vòng lặp tham chiếu.
  - **Hàm `_transform()`:** Chuyển đổi từng object/list/dict thành dạng đã được thay thế bằng các chỉ mục tham chiếu. Với list, nó duyệt từng phần tử; với dict, nó duyệt từng key; với kiểu nguyên thủy thì giữ nguyên.
  - **Hàm `stringify()`:** Khởi tạo `_Known`, `input`, `output`, đăng ký object gốc đầu tiên rồi lặp qua toàn bộ mảng `input` để biến từng phần tử thành dạng flatted thông qua `_transform()`. Cuối cùng gọi `_json.dumps(output, *args, **kwargs)` để xuất chuỗi JSON.
  - **Hàm `_wrap()`:** Được dùng trong quá trình parse để duyệt đệ quy JSON đã load và bọc mọi chuỗi bằng `_String`, giúp bước giải tham chiếu hoạt động chính xác.
  - **Hàm `_resolver()`:** Tạo ra một hàm con `resolver()` có nhiệm vụ thay thế `_String(index)` bằng object thật nằm ở vị trí tương ứng trong mảng `input`. Nếu object được phục hồi vẫn chứa tham chiếu lồng sâu, nó thêm vào danh sách `lazy` để xử lý tiếp.
  - **Hàm `parse()`:** Dùng `_json.loads()` đọc chuỗi JSON flatted thành mảng, bọc string bằng `_wrap()`, xây dựng danh sách input, khôi phục object gốc `input[0]`, sau đó xử lý danh sách `lazy` cho đến khi toàn bộ tham chiếu vòng được nối lại hoàn chỉnh.
* **Lưu ý:** Đây là thư viện phụ thuộc sinh ra trong `frontend/node_modules`, không phải mã nguồn chính do nhóm dự án viết. Tuy nhiên, vì nó là file `.py` tồn tại trong cây thư mục dự án nên vẫn được mô tả trong tài liệu để đầy đủ cấu trúc.

---
*Tài liệu được cập nhật tự động vào ngày 01 tháng 06 năm 2026.*
