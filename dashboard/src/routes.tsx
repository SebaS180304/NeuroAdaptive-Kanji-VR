import { Navigate, type RouteObject } from 'react-router'
import { AppShell } from '@/components/shell/AppShell'
import { ReservedScreen } from '@/components/shell/ReservedScreen'
import { ParticipantList } from '@/features/participants/ParticipantList'
import { TokensPage } from '@/features/tokens/TokensPage'

// One route per v1 screen (stack-and-structure.md). Each renders its reserved
// placeholder until its task builds it.
export const routes: RouteObject[] = [
  {
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to="/sessions" replace /> },
      { path: 'sessions', element: <ReservedScreen title="Sessions" thing="Session list" /> },
      { path: 'sessions/:sessionId', element: <ReservedScreen title="Session" thing="Session View" /> },
      { path: 'participants', element: <ParticipantList /> },
      { path: 'participants/:participantId', element: <ReservedScreen title="Participant" thing="Participant View" /> },
      { path: 'pretest', element: <ReservedScreen title="Kanji pre-test" thing="Kanji pre-test" /> },
      { path: 'quality', element: <ReservedScreen title="Data quality" thing="Data quality" /> },
    ],
  },
  // Development reference, outside the rail: the tokens in both themes.
  { path: 'tokens', element: <TokensPage /> },
]
