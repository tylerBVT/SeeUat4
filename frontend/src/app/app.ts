import { Component, inject } from '@angular/core';
import { SeeUat4Api } from './api';
import { LockPanel } from './lock-panel/lock-panel';
import { StatusCard } from './status-card/status-card';
import { UnlockPanel } from './unlock-panel/unlock-panel';

@Component({
  selector: 'app-root',
  imports: [StatusCard, LockPanel, UnlockPanel],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  protected readonly api = inject(SeeUat4Api);
}
