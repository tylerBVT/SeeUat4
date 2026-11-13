import { Component, input, signal } from '@angular/core';

@Component({
  selector: 'app-lock-panel',
  templateUrl: './lock-panel.html',
  styleUrl: './lock-panel.css',
})
export class LockPanel {
  readonly enabled = input.required<boolean>();
  readonly command = input.required<string>();
  protected readonly copied = signal(false);

  protected async copy(): Promise<void> {
    await navigator.clipboard.writeText(this.command());
    this.copied.set(true);
    setTimeout(() => this.copied.set(false), 2000);
  }
}
