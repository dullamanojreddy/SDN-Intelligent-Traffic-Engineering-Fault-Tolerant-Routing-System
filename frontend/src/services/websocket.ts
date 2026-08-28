type MessageCallback = (data: any) => void;

class WebSocketClient {
  private ws: WebSocket | null = null;
  private listeners: MessageCallback[] = [];
  private reconnectInterval = 3000;
  private url: string;

  constructor() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    this.url = `${protocol}//${window.location.host}/ws/network`;
  }

  public connect() {
    try {
      this.ws = new WebSocket(this.url);
      
      this.ws.onopen = () => {
        console.log('[WebSocket] Connected to SDN controller gateway.');
      };

      this.ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          this.listeners.forEach((callback) => callback(payload));
        } catch (e) {
          console.error('[WebSocket] Message parsing error', e);
        }
      };

      this.ws.onclose = () => {
        console.warn('[WebSocket] Connection closed. Attempting reconnect...');
        setTimeout(() => this.connect(), this.reconnectInterval);
      };

      this.ws.onerror = (err) => {
        console.error('[WebSocket] Connection error:', err);
        this.ws?.close();
      };
    } catch (err) {
      console.error('[WebSocket] Setup exception:', err);
    }
  }

  public subscribe(callback: MessageCallback) {
    this.listeners.push(callback);
    return () => {
      this.listeners = this.listeners.filter((cb) => cb !== callback);
    };
  }

  public send(data: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }
}

export const wsClient = new WebSocketClient();
