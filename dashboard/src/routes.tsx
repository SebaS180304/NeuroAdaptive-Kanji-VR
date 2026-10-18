import { Navigate, type RouteObject } from 'react-router'
import { AppShell } from '@/components/shell/AppShell'
import { ReservedScreen } from '@/components/shell/ReservedScreen'
import { ParticipantList } from '@/features/participants/ParticipantList'
import { PretestPick } from '@/features/pretest/PretestPick'
import { RegisterParticipant } from '@/features/pretest/RegisterParticipant'
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
      { path: 'pretest', element: <PretestPick /> },
      { path: 'pretest/:participantId', element: <ReservedScreen title="Kanji pre-test" thing="One kanji at a time" /> },
      { path: 'quality', element: <ReservedScreen title="Data quality" thing="Data quality" /> },
    ],
  },
  // V1.10 Register has its own top bar and no rail.
  { path: 'pretest/register', element: <RegisterParticipant /> },
  // Development reference, outside the rail: the tokens in both themes.
  { path: 'tokens', element: <TokensPage /> },
]
