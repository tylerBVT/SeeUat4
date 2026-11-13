import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

export type Phase = 'idle' | 'waiting' | 'confirm' | 'unlocked' | 'lockout';

export interface UnlockState {
  phase: Phase;
  secondsLeft: number;
  command?: string;
}

export interface AppState {
  mode: 'LOCKED' | 'UNLOCKED';
  lastUnlockedAt: string | null;
  lockCommand: string;
  unlock: UnlockState;
}

/** Talks to server/server.py. All timers and password checks live there. */
@Injectable({ providedIn: 'root' })
export class SeeUat4Api {
  private readonly http = inject(HttpClient);

  readonly state = signal<AppState | null>(null);
  readonly offline = signal(false);

  constructor() {
    this.refresh();
    setInterval(() => this.refresh(), 1000);
  }

  async refresh(): Promise<void> {
    try {
      this.state.set(await firstValueFrom(this.http.get<AppState>('/api/state')));
      this.offline.set(false);
    } catch {
      this.offline.set(true);
    }
  }

  /** Step 1: first password. Returns an error message, or null on success. */
  start(password: string): Promise<string | null> {
    return this.post('/api/unlock/start', password);
  }

  /** Step 2: confirm password after the wait. Returns an error message, or null. */
  confirm(password: string): Promise<string | null> {
    return this.post('/api/unlock/confirm', password);
  }

  private async post(url: string, password: string): Promise<string | null> {
    try {
      await firstValueFrom(this.http.post(url, { password }));
      await this.refresh();
      return null;
    } catch (e) {
      await this.refresh();
      if (e instanceof HttpErrorResponse && e.error?.error) {
        return e.error.error as string;
      }
      return 'Cannot reach the server.';
    }
  }
}
