import { useEffect, useRef } from 'react';
import { useAppDispatch, useAppSelector } from '../../store/hooks';
import {
  hydrateGame,
  markTrainingCompleted,
  grantVerifiedObserverBadge,
  resetCommunityGame,
} from '../../store/slices/communityGameSlice';
import type { CommunityGamePersistedState } from '../../store/slices/communityGameSlice';
import {
  mergeGuestIntoUser,
  readPersistedGame,
  storageKeyForUser,
  writePersistedGame,
} from '../../gamification/persistence';
import { fetchCommunityGameState, saveCommunityGameState } from '../../services/api/communityGame';
import { isEmailVerified } from '../../utils/emailVerified';

function pickPersisted(s: {
  totalXp: number;
  lifetimeSightings: number;
  questWeekKey: string;
  weeklySightings: number;
  weeklyGpsSightings: number;
  weeklyExtraSightings: number;
  weeksWithUpload: string[];
  gpsHintTotal: number;
  manualHintTotal: number;
  sightingsWithExtraPhotos: number;
  trainingCompleted: boolean;
  badges: string[];
  completedWeeklyQuestIds: string[];
}): CommunityGamePersistedState {
  return {
    totalXp: s.totalXp,
    lifetimeSightings: s.lifetimeSightings,
    questWeekKey: s.questWeekKey,
    weeklySightings: s.weeklySightings,
    weeklyGpsSightings: s.weeklyGpsSightings,
    weeklyExtraSightings: s.weeklyExtraSightings,
    weeksWithUpload: [...s.weeksWithUpload],
    gpsHintTotal: s.gpsHintTotal,
    manualHintTotal: s.manualHintTotal,
    sightingsWithExtraPhotos: s.sightingsWithExtraPhotos,
    trainingCompleted: s.trainingCompleted,
    badges: [...s.badges],
    completedWeeklyQuestIds: [...s.completedWeeklyQuestIds],
  };
}

/**
 * Loads / saves observer gamification: guests → localStorage; community accounts → auth API + auth.json store.
 */
export default function GamePersistence(): null {
  const dispatch = useAppDispatch();
  const authChecked = useAppSelector((s) => s.user.authChecked);
  const userId = useAppSelector((s) => s.user.user?.id ?? null);
  const role = useAppSelector((s) => s.user.role);
  const user = useAppSelector((s) => s.user.user);
  const game = useAppSelector((s) => s.communityGame);

  /** When false, debounced PUT is skipped (during initial server merge for community users). */
  const serverWriteEnabledRef = useRef(true);

  useEffect(() => {
    if (!authChecked) return;

    let cancelled = false;

    const applyInstructionsFlag = (): void => {
      try {
        if (localStorage.getItem('hasSeenInstructions') === 'true') {
          dispatch(markTrainingCompleted());
        }
      } catch {
        /* ignore */
      }
    };

    void (async () => {
      if (userId != null && role !== 'community') {
        serverWriteEnabledRef.current = false;
        dispatch(resetCommunityGame());
        return;
      }

      if (userId == null) {
        serverWriteEnabledRef.current = true;
        const guestKey = storageKeyForUser(null);
        const loaded = readPersistedGame(guestKey);
        dispatch(hydrateGame(loaded ?? {}));
        if (!cancelled) {
          applyInstructionsFlag();
        }
        return;
      }

      serverWriteEnabledRef.current = false;
      const guestKey = storageKeyForUser(null);
      const guestData = readPersistedGame(guestKey);

      let serverData: CommunityGamePersistedState | null = null;
      try {
        serverData = await fetchCommunityGameState();
      } catch {
        serverData = readPersistedGame(storageKeyForUser(userId));
      }

      if (cancelled) return;

      const merged = mergeGuestIntoUser(serverData, guestData);

      if (guestData && guestData.lifetimeSightings > 0) {
        try {
          localStorage.removeItem(guestKey);
        } catch {
          /* ignore */
        }
      }

      dispatch(hydrateGame(merged));

      const serverNorm = serverData ? JSON.stringify(serverData) : 'null';
      const mergedNorm = JSON.stringify(merged);
      const guestHad = !!(guestData && guestData.lifetimeSightings > 0);
      if (guestHad || mergedNorm !== serverNorm) {
        try {
          await saveCommunityGameState(merged);
        } catch {
          /* offline — next debounced save may succeed */
        }
      }

      try {
        localStorage.removeItem(storageKeyForUser(userId));
      } catch {
        /* ignore */
      }

      if (cancelled) return;

      applyInstructionsFlag();
      serverWriteEnabledRef.current = true;
    })();

    return () => {
      cancelled = true;
    };
  }, [authChecked, userId, role, dispatch]);

  useEffect(() => {
    if (!authChecked || !user) return;
    if (isEmailVerified(user)) {
      dispatch(grantVerifiedObserverBadge());
    }
  }, [authChecked, user?.id, user?.email_verified, dispatch]);

  useEffect(() => {
    if (!authChecked || !game.hydrated) return;

    if (userId == null) {
      writePersistedGame(storageKeyForUser(null), pickPersisted(game));
      return;
    }

    if (role !== 'community') return;
    if (!serverWriteEnabledRef.current) return;

    const uid = userId;
    const snapshot = pickPersisted(game);
    const t = window.setTimeout(() => {
      saveCommunityGameState(snapshot)
        .then(() => {
          try {
            localStorage.removeItem(storageKeyForUser(uid));
          } catch {
            /* ignore */
          }
        })
        .catch(() => {
          /* offline */
        });
    }, 450);
    return () => clearTimeout(t);
  }, [
    authChecked,
    userId,
    role,
    game.hydrated,
    game.totalXp,
    game.lifetimeSightings,
    game.questWeekKey,
    game.weeklySightings,
    game.weeklyGpsSightings,
    game.weeklyExtraSightings,
    game.weeksWithUpload,
    game.gpsHintTotal,
    game.manualHintTotal,
    game.sightingsWithExtraPhotos,
    game.trainingCompleted,
    game.badges,
    game.completedWeeklyQuestIds,
  ]);

  return null;
}
