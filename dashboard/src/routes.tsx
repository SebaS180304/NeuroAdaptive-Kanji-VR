import { Navigate, type RouteObject } from 'react-router'
import { AppShell } from '@/components/shell/AppShell'
import { ReservedScreen } from '@/components/shell/ReservedScreen'
import { ParticipantList } from '@/features/participants/ParticipantList'
import { PretestPick } from '@/features/pretest/PretestPick'
import { PretestRun } from '@/features/pretest/PretestRun'
import { RegisterParticipant } from '@/features/pretest/RegisterParticipant'
import { SessionList } from '@/features/sessions/SessionList'
import { SessionView } from '@/features/sessions/SessionView'
import { TokensPage } from '@/features/tokens/TokensPage'

// One route per v1 screen (stack-and-structure.md). Each renders its reserved
// placeholder until its task builds it.
export const routes: RouteObject[] = [
  {
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to="/sessions" replace /> },
      { path: 'sessions', element: <SessionList /> },
      { path: 'sessions/:sessionId', element: <SessionView /> },
      { path: 'participants', element: <ParticipantList /> },
      { path: 'participants/:participantId', element: <ReservedScreen title="Participant" thing="Participant View" /> },
      { path: 'pretest', element: <PretestPick /> },
      { path: 'quality', element: <ReservedScreen title="Data quality" thing="Data quality" /> },
    ],
  },
  // V1.10 Register has its own top bar and no rail.
  { path: 'pretest/register', element: <RegisterParticipant /> },
  // V1.10 One kanji and Complete: focus mode, no rail (the participant looks at it).
  { path: 'pretest/:participantId', element: <PretestRun /> },
  // Development reference, outside the rail: the tokens in both themes.
  { path: 'tokens', element: <TokensPage /> },
]
