import { useEffect, useRef, useState } from "react";
import { createChart } from "lightweight-charts";
import { getStreamLatest } from "../api";

const chartColors = [
  "#2563eb", "#16a34a", "#dc2626", "#d97706", "#7c3aed",
  "#0891b2", "#db2777", "#4b5563", "#4f46e5", "#059669"
];

export default function RealtimeChart() {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const [activeTickers, setActiveTickers] = useState<string[]>([]);
  const [tickersList, setTickersList] = useState<string[]>([]);
  const chartRef = useRef<any>(null);
  const seriesRef = useRef<{ [key: string]: any }>({});
  const historyRef = useRef<{ [key: string]: { time: number; value: number }[] }>({});

  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Khởi tạo Lightweight Chart
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 450,
      layout: {
        background: { color: "#ffffff" },
        textColor: "#333333",
      },
      grid: {
        vertLines: { color: "#f0f3fa" },
        horzLines: { color: "#f0f3fa" },
      },
      timeScale: {
        borderColor: "#dfe2e9",
        timeVisible: true,
        secondsVisible: false,
      },
    });

    chartRef.current = chart;

    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.resize(chartContainerRef.current.clientWidth, 450);
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    let active = true;

    const updateChart = () => {
      getStreamLatest()
        .then((points) => {
          if (!active || !chartRef.current) return;

          // Cập nhật danh sách các ticker
          const list = points.map((p) => p.ticker);
          setTickersList(list);

          if (activeTickers.length === 0 && list.length > 0) {
            // Mặc định chọn 3 mã đầu tiên vẽ đồ thị
            setActiveTickers(list.slice(0, 3));
          }

          const timestamp = Math.floor(new Date(points[0].timestamp).getTime() / 1000);

          points.forEach((p) => {
            const percentChange = ((p.runtime_price - p.last_close) / p.last_close) * 100;
            if (!historyRef.current[p.ticker]) {
              historyRef.current[p.ticker] = [];
            }
            historyRef.current[p.ticker].push({ time: timestamp, value: percentChange });
            if (historyRef.current[p.ticker].length > 100) {
              historyRef.current[p.ticker].shift();
            }
          });

          // Vẽ lại các đường được active
          activeTickers.forEach((tk, idx) => {
            if (!seriesRef.current[tk] && chartRef.current) {
              seriesRef.current[tk] = chartRef.current.addLineSeries({
                color: chartColors[idx % chartColors.length],
                lineWidth: 2.5,
                title: tk,
              });
            }

            const data = historyRef.current[tk] || [];
            if (seriesRef.current[tk]) {
              seriesRef.current[tk].setData(data);
            }
          });

          // Loại bỏ các đường không được active
          Object.keys(seriesRef.current).forEach((tk) => {
            if (!activeTickers.includes(tk) && chartRef.current) {
              chartRef.current.removeSeries(seriesRef.current[tk]);
              delete seriesRef.current[tk];
            }
          });
        })
        .catch((err) => console.error("Error loading stream point for chart", err));
    };

    updateChart();
    const interval = setInterval(updateChart, 3000);

    return () => {
      active = false;
      clearInterval(interval);
    };
  }, [activeTickers]);

  const handleCheckboxChange = (ticker: string) => {
    if (activeTickers.includes(ticker)) {
      if (activeTickers.length > 1) {
        setActiveTickers(activeTickers.filter((t) => t !== ticker));
      }
    } else {
      setActiveTickers([...activeTickers, ticker]);
    }
  };

  return (
    <div className="grid grid-cols-12 gap-6 bg-white shadow rounded-2xl p-6">
      <div className="col-span-9 space-y-4">
        <div className="flex justify-between items-center border-b pb-3">
          <div>
            <h2 className="text-xl font-bold text-slate-800">Biểu Đồ Thời Gian Thực</h2>
            <div className="flex gap-2 mt-2">
              <span className="bg-amber-100 text-amber-800 text-xs font-semibold px-2.5 py-1 rounded-full">Chế độ Mô phỏng</span>
              <span className="bg-green-100 text-green-800 text-xs font-semibold px-2.5 py-1 rounded-full">Đang kết nối trực tuyến</span>
            </div>
          </div>
        </div>
        <div ref={chartContainerRef} style={{ width: "100%", height: "450px" }}></div>
      </div>

      <div className="col-span-3 border-l pl-6 space-y-3">
        <h3 className="font-bold text-slate-700 text-sm border-b pb-2">Mã theo dõi trên biểu đồ</h3>
        <div className="flex flex-col gap-2.5 max-h-[420px] overflow-y-auto">
          {tickersList.map((ticker) => (
            <label key={ticker} className="flex items-center gap-3 cursor-pointer hover:bg-slate-50 p-1 rounded-lg">
              <input
                type="checkbox"
                checked={activeTickers.includes(ticker)}
                onChange={() => handleCheckboxChange(ticker)}
                className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <span className="font-bold text-slate-700 text-sm">{ticker}</span>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}
