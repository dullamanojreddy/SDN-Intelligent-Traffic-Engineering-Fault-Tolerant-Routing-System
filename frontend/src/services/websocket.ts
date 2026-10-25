type MessageCallback = (data: any) => void;

class WebSocketClient {
  private ws: WebSocket | null = null;
  private listeners: MessageCallback[] = [];
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectDelay = 3000;
  private manuallyClosed = false;
  private connecting = false;
  private url: string;

  constructor() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    this.url = `${protocol}//${window.location.host}/ws/network`;
  }

  public connect() {
    this.manuallyClosed = false;
    if (
      this.manuallyClosed ||
      this.connecting ||
      (this.ws && (
        this.ws.readyState === WebSocket.OPEN ||
        this.ws.readyState === WebSocket.CONNECTING
      ))
    ) {
      return;
    }

    this.connecting = true;
    try {
      const socket = new WebSocket(this.url);
      this.ws = socket;
      
      socket.onopen = () => {
        if (this.ws !== socket) {
          return;
        }
        this.connecting = false;
        this.reconnectDelay = 3000;
        console.log('[WebSocket] Connected to SDN controller gateway.');
      };

      socket.onmessage = (event) => {
        if (this.ws !== socket) {
          return;
        }
        try {
          const payload = JSON.parse(event.data);
          this.listeners.forEach((callback) => callback(payload));
        } catch (e) {
          console.error('[WebSocket] Message parsing error', e);
        }
      };

      socket.onclose = () => {
        if (this.ws !== socket) {
          return;
        }
        this.connecting = false;
        this.ws = null;
        if (!this.manuallyClosed && !this.reconnectTimer) {
          this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = null;
            this.connect();
            this.reconnectDelay = Math.min(this.reconnectDelay * 2, 30000);
          }, this.reconnectDelay);
        }
      };

      socket.onerror = () => {
        if (this.ws !== socket) {
          return;
        }
        this.connecting = false;
        if (!this.manuallyClosed) {
          console.warn('[WebSocket] Backend WebSocket unavailable; retrying.');
        }
      };
    } catch (err) {
      this.connecting = false;
      console.error('[WebSocket] Setup exception:', err);
    }
  }

  public disconnect() {
    this.manuallyClosed = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    const socket = this.ws;
    this.ws = null;
    this.connecting = false;
    socket?.close();
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
