import { Component, inject, input, signal } from '@angular/core';
import { SeeUat4Api, UnlockState } from '../api';
import { mmss } from '../clock';

@Component({
  selector: 'app-unlock-panel',
  templateUrl: './unlock-panel.html',
  styleUrl: './unlock-panel.css',
})
export class UnlockPanel {
  private readonly api = inject(SeeUat4Api);

  readonly enabled = input.required<boolean>();
  readonly unlock = input.required<UnlockState>();

  protected readonly password = signal('');
  protected readonly error = signal<string | null>(null);
  protected readonly busy = signal(false);
  protected readonly copied = signal(false);
  protected readonly mmss = mmss;

  protected onInput(event: Event): void {
    this.password.set((event.target as HTMLInputElement).value);
  }

  protected async submit(): Promise<void> {
    if (this.busy() || !this.password().trim()) return;
    this.busy.set(true);
    const phase = this.unlock().phase;
    const err = phase === 'confirm'
      ? await this.api.confirm(this.password())
      : await this.api.start(this.password());
    this.error.set(err);
    this.password.set('');
    this.busy.set(false);
  }

  protected async copy(command: string): Promise<void> {
    await navigator.clipboard.writeText(command);
    this.copied.set(true);
    setTimeout(() => this.copied.set(false), 2000);
  }
}
