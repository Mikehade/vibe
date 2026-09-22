# Vibe Frontend

React 18 / TypeScript / Vite frontend for the Vibe Session Architect. Designed for Fire TV's 10-foot UI with D-pad navigation, but works in any browser for development and testing.

## Setup

### Prerequisites

- Node.js 20+
- Backend running at http://localhost:8000 (or via Docker Compose)

### Install & Run

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open http://localhost:5173 in your browser.

### Build

```bash
npm run build       # Production build → dist/
npm run preview     # Preview production build locally
npm run type-check  # TypeScript check without building
```

## How It Works

### Device ID (Auto-Generated)

The app automatically generates a UUID device ID on first visit and stores it in `localStorage`. Every API call includes this as the `X-Device-ID` header — no login or registration needed. To simulate a fresh device, clear localStorage or use incognito mode.

### App Flow

```
First visit → Onboarding (genres + providers)
                ↓
         Mood Selection (6 moods)
                ↓
         Time Budget (optional)
                ↓
     Plan Generation (NDJSON streaming)
      → Trajectory event (energy arc)
      → Pick events (one per title, progressive)
      → Summary event (final stats)
                ↓
         Plan View (horizontal rail)
      → Click/select pick for detail overlay
      → Mark as watching/watched/skipped
                ↓
         Feedback (thumbs up/down per session + per pick)
                ↓
              Loop ↻
```

### Fire TV / D-Pad Navigation

The `useDpad` hook maps keyboard events to Fire TV remote actions:

| Key | Action |
|-----|--------|
| Arrow keys | Navigate focus between elements |
| Enter / Space | Select focused element |
| Escape / Backspace | Go back |

All interactive components track a focus index and render a visible focus ring. This works with keyboard in the browser and maps directly to the Fire TV remote.

## Project Structure

```
src/
├── api/
│   └── client.ts              # API client + NDJSON stream generator
│
├── stores/
│   ├── sessionStore.ts        # Plan generation, streaming, history
│   └── profileStore.ts        # Profile, onboarding wizard state
│
├── hooks/
│   ├── useDpad.ts             # D-pad keyboard navigation
│   └── useStreamPlan.ts       # Convenience wrapper for streaming
│
├── components/
│   ├── common/
│   │   ├── FocusableButton.tsx # TV-friendly button with focus ring
│   │   ├── PosterCard.tsx     # Movie poster with role badge + details
│   │   └── LoadingPulse.tsx   # Streaming phase indicator
│   ├── onboarding/
│   │   ├── GenreSelector.tsx  # Genre preference cards (like/skip/dislike)
│   │   └── ProviderSelector.tsx # Streaming service picker
│   ├── session/
│   │   ├── MoodPicker.tsx     # 6-mood grid selector
│   │   ├── TimeBudget.tsx     # Time preset picker
│   │   └── PlanView.tsx       # Session plan rail + pick detail overlay
│   └── feedback/
│       └── SessionFeedback.tsx # Post-session rating form
│
├── pages/
│   ├── OnboardingPage.tsx     # 2-step wizard (genres → providers)
│   ├── SessionPage.tsx        # Main flow (mood → time → plan → feedback)
│   └── HistoryPage.tsx        # Past sessions list
│
├── types/
│   └── index.ts               # Domain types + stream event types
│
├── styles/
│   └── index.css              # Tailwind base + TV tokens
│
├── App.tsx                    # Router + onboarding gate
└── main.tsx                   # React root
```

## Design System

Tailwind-based with custom TV-first tokens:

| Token | Value | Purpose |
|-------|-------|---------|
| `text-tv-sm` | 1.125rem | Small TV text |
| `text-tv-base` | 1.375rem | Default TV text |
| `text-tv-lg` | 1.75rem | Large TV text |
| `text-tv-xl` | 2.25rem | Headings |
| `text-tv-2xl` | 3rem | Hero text |
| `rounded-tv` | 1rem | Card/button radius |
| `bg-vibe-bg` | #0a0a0f | Dark background |
| `bg-vibe-surface` | #14141f | Surface |
| `bg-vibe-card` | #1c1c2e | Card background |
| `text-vibe-accent` | #6c5ce7 | Primary accent (purple) |
| `text-vibe-success` | #00b894 | Positive feedback |
| `text-vibe-danger` | #e17055 | Negative feedback |

## NDJSON Streaming

The plan generation endpoint streams newline-delimited JSON events. The API client uses `ReadableStream` to parse them progressively:

```typescript
for await (const event of streamPlan('chill', 120)) {
  switch (event.type) {
    case 'trajectory': // energy arc decided
    case 'pick':       // one title added to plan
    case 'summary':    // plan complete
    case 'error':      // something went wrong
  }
}
```

The Zustand store updates state for each event, so React components re-render progressively as picks arrive — the user sees titles appear one by one.

## Testing in Browser

The app is fully testable in any desktop browser. The D-pad navigation maps to arrow keys + Enter, so you can navigate the entire UI with just the keyboard, simulating the Fire TV experience.

For multiple test users, open in separate incognito windows — each gets a fresh device ID and independent taste profile.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `/api/v1` | Backend API base URL. In Docker, the Vite dev server proxies `/api` to the backend container. For local dev without Docker, set to `http://localhost:8000/api/v1`. |
