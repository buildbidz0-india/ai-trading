export interface Ticker {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  high: number;
  low: number;
}

export interface Order {
  id: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  type: 'MARKET' | 'LIMIT';
  quantity: number;
  price: number;
  status: 'PENDING' | 'FILLED' | 'CANCELLED' | 'REJECTED';
  timestamp: number;
  // Backend fields
  exchange?: string;
  order_type?: string;
  product_type?: string;
  broker_order_id?: string;
  rejection_reason?: string;
  source?: string;
}

export interface Position {
  id?: string;
  symbol: string;
  quantity: number;
  averagePrice: number;
  currentPrice: number;
  pnl: number;
  pnlPercent: number;
  // Backend fields
  instrument_id?: string;
  exchange?: string;
  net_quantity?: number;
  realised_pnl?: string;
  unrealised_pnl?: string;
  greeks?: {
    delta: number;
    gamma: number;
    theta: number;
    vega: number;
    rho: number;
  };
}

export interface MarketState {
  isConnected: boolean;
  latency: number;
  lastUpdate: number;
}

// Backend DTO types
export interface PlaceOrderRequest {
  symbol: string;
  exchange: string;
  side: string;
  order_type: string;
  product_type: string;
  quantity: number;
  price: number;
  trigger_price: number;
  source: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
}

export interface OrderResponse {
  id: string;
  symbol: string;
  exchange: string;
  side: string;
  order_type: string;
  product_type: string;
  quantity: number;
  price: string;
  status: string;
  broker_order_id: string | null;
  rejection_reason: string | null;
  source: string;
  created_at: string;
  updated_at: string;
}

export interface PositionResponse {
  id: string;
  instrument_id: string;
  symbol: string;
  exchange: string;
  net_quantity: number;
  average_price: string;
  realised_pnl: string;
  unrealised_pnl: string;
  greeks: {
    delta: number;
    gamma: number;
    theta: number;
    vega: number;
    rho: number;
  };
  updated_at: string;
}

export interface TradeResponse {
  id: string;
  order_id: string;
  symbol: string;
  exchange: string;
  side: string;
  quantity: number;
  price: string;
  fees: string;
  executed_at: string;
}
