import { Component, input } from '@angular/core';
import { DatePipe } from '@angular/common';
import { AppState } from '../api';

@Component({
  selector: 'app-status-card',
  imports: [DatePipe],
  templateUrl: './status-card.html',
  styleUrl: './status-card.css',
})
export class StatusCard {
  readonly state = input.required<AppState>();
}
