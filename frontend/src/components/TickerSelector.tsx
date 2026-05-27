import { useEffect, useState } from "react";
import { ChevronDown } from "lucide-react";
import { getTickers, APIError } from "../api";

type TickerSelectorProps = {
  onSelectTicker: (ticker: string) => void;
  placeholder?: string;
};

export default function TickerSelector({
  onSelectTicker,
  placeholder = "Select a ticker...",
}: TickerSelectorProps) {
  const [tickers, setTickers] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);

    getTickers()
      .then((data) => {
        setTickers(data.tickers);
        setLoading(false);
      })
      .catch((err) => {
        if (err instanceof APIError) {
          setError(err.detail || err.message);
        } else {
          setError("Failed to load tickers");
        }
        setLoading(false);
      });
  }, []);

  const handleSelect = (ticker: string) => {
    setSelected(ticker);
    onSelectTicker(ticker);
    setIsOpen(false);
  };

  if (loading) {
    return (
      <div className="px-4 py-2 border rounded-lg bg-gray-50 text-gray-400 text-sm">
        Loading tickers...
      </div>
    );
  }

  if (error) {
    return (
      <div className="px-4 py-2 border border-red-300 rounded-lg bg-red-50 text-red-600 text-sm">
        {error}
      </div>
    );
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-4 py-2 border rounded-lg bg-white hover:bg-gray-50 transition text-sm font-medium"
      >
        {selected || placeholder}
        <ChevronDown className="w-4 h-4" />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-2 w-48 border rounded-lg bg-white shadow-lg z-10 max-h-64 overflow-y-auto">
          {tickers.map((ticker) => (
            <button
              key={ticker}
              onClick={() => handleSelect(ticker)}
              className={`block w-full text-left px-4 py-2 hover:bg-blue-50 transition ${
                selected === ticker
                  ? "bg-blue-100 text-blue-700 font-semibold"
                  : "text-gray-700"
              }`}
            >
              {ticker}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
