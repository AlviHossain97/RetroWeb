/**
 * WebRTC Netplay — serverless peer-to-peer multiplayer.
 *
 * Flow:
 *   1. Host creates offer → copies it (base64 encoded SDP)
 *   2. Guest pastes offer → creates answer → copies it
 *   3. Host pastes answer → connection established
 *   4. Input frames are exchanged over a DataChannel
 */

export type NetplayRole = "host" | "guest";

export interface NetplayInput {
  frame: number;
  buttons: number; // bitmask of pressed buttons
}

export interface NetplayState {
  role: NetplayRole;
  connected: boolean;
  remoteInput: NetplayInput | null;
}

type OnStateChange = (state: NetplayState) => void;
type OnRemoteInput = (input: NetplayInput) => void;

const RTC_CONFIG: RTCConfiguration = {
  iceServers: [
    { urls: "stun:stun.l.google.com:19302" },
    { urls: "stun:stun1.l.google.com:19302" },
  ],
};

export class NetplaySession {
  private pc: RTCPeerConnection;
  private dc: RTCDataChannel | null = null;
  private role: NetplayRole;
  private _connected = false;
  private onStateChange: OnStateChange;
  private onRemoteInput: OnRemoteInput;
  private iceGatheringDone = false;

  constructor(
    role: NetplayRole,
    onStateChange: OnStateChange,
    onRemoteInput: OnRemoteInput,
  ) {
    this.role = role;
    this.onStateChange = onStateChange;
    this.onRemoteInput = onRemoteInput;
    this.pc = new RTCPeerConnection(RTC_CONFIG);

    this.pc.onicecandidate = (e) => {
      if (!e.candidate) {
        this.iceGatheringDone = true;
      }
    };

    this.pc.onconnectionstatechange = () => {
      const state = this.pc.connectionState;
      if (state === "connected") {
        this._connected = true;
        this.emitState();
      } else if (state === "disconnected" || state === "failed" || state === "closed") {
        this._connected = false;
        this.emitState();
      }
    };

    if (role === "host") {
      this.dc = this.pc.createDataChannel("netplay", { ordered: true });
      this.setupDataChannel(this.dc);
    } else {
      this.pc.ondatachannel = (e) => {
        this.dc = e.channel;
        this.setupDataChannel(this.dc);
      };
    }
  }

  private setupDataChannel(dc: RTCDataChannel) {
    dc.onopen = () => {
      this._connected = true;
      this.emitState();
    };
    dc.onclose = () => {
      this._connected = false;
      this.emitState();
    };
    dc.onmessage = (e) => {
      try {
        const input = JSON.parse(e.data) as NetplayInput;
        this.onRemoteInput(input);
      } catch {
        // Ignore malformed messages
      }
    };
  }

  private emitState() {
    this.onStateChange({
      role: this.role,
      connected: this._connected,
      remoteInput: null,
    });
  }

  /** Wait for ICE gathering to complete (up to timeout ms) */
  private async waitForIce(timeout = 5000): Promise<void> {
    if (this.iceGatheringDone) return;
    return new Promise((resolve) => {
      const timer = setTimeout(resolve, timeout);
      this.pc.onicegatheringstatechange = () => {
        if (this.pc.iceGatheringState === "complete") {
          clearTimeout(timer);
          resolve();
        }
      };
    });
  }

  /** Host: create offer, returns base64-encoded SDP to share */
  async createOffer(): Promise<string> {
    const offer = await this.pc.createOffer();
    await this.pc.setLocalDescription(offer);
    await this.waitForIce();
    const sdp = this.pc.localDescription;
    return btoa(JSON.stringify(sdp));
  }

  /** Guest: accept host's offer, returns base64-encoded answer */
  async acceptOffer(offerB64: string): Promise<string> {
    const offer = JSON.parse(atob(offerB64)) as RTCSessionDescriptionInit;
    await this.pc.setRemoteDescription(new RTCSessionDescription(offer));
    const answer = await this.pc.createAnswer();
    await this.pc.setLocalDescription(answer);
    await this.waitForIce();
    const sdp = this.pc.localDescription;
    return btoa(JSON.stringify(sdp));
  }

  /** Host: accept guest's answer to complete connection */
  async acceptAnswer(answerB64: string): Promise<void> {
    const answer = JSON.parse(atob(answerB64)) as RTCSessionDescriptionInit;
    await this.pc.setRemoteDescription(new RTCSessionDescription(answer));
  }

  /** Send local player's input to the remote peer */
  sendInput(input: NetplayInput): void {
    if (this.dc?.readyState === "open") {
      this.dc.send(JSON.stringify(input));
    }
  }

  /** Convert current keyboard/gamepad state to a button bitmask */
  static buttonsToMask(buttons: Record<string, boolean>): number {
    const order = [
      "a", "b", "x", "y",
      "dpadUp", "dpadDown", "dpadLeft", "dpadRight",
      "lb", "rb", "lt", "rt",
      "minus", "plus", "l3", "r3",
    ];
    let mask = 0;
    for (let i = 0; i < order.length; i++) {
      if (buttons[order[i]]) mask |= (1 << i);
    }
    return mask;
  }

  /** Convert bitmask back to button state */
  static maskToButtons(mask: number): Record<string, boolean> {
    const order = [
      "a", "b", "x", "y",
      "dpadUp", "dpadDown", "dpadLeft", "dpadRight",
      "lb", "rb", "lt", "rt",
      "minus", "plus", "l3", "r3",
    ];
    const result: Record<string, boolean> = {};
    for (let i = 0; i < order.length; i++) {
      result[order[i]] = !!(mask & (1 << i));
    }
    return result;
  }

  get isConnected(): boolean {
    return this._connected;
  }

  destroy(): void {
    this.dc?.close();
    this.pc.close();
    this._connected = false;
  }
}
