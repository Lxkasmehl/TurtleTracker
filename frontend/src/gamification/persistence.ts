import {
  GAME_STORAGE_PREFIX,
  GAME_STORAGE_VERSION,
  type CommunityGamePersistedState,
} from './definitions';

export function storageKeyForUser(userId: number | null): string {
  if (userId == null) return `${GAME_STORAGE_PREFIX}_guest`;
  return `${GAME_STORAGE_PREFIX}_uid_${userId}`;
}

export function readPersistedGame(key: string): CommunityGamePersistedState | null {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { v?: number; state?: CommunityGamePersistedState };
    if (parsed?.v !== GAME_STORAGE_VERSION || !parsed.state) return null;
    return parsed.state;
  } catch {
    return null;
  }
}

export function writePersistedGame(key: string, state: CommunityGamePersistedState): void {
  try {
    localStorage.setItem(
      key,
      JSON.stringify({ v: GAME_STORAGE_VERSION, state }),
    );
  } catch {
    /* quota or private mode */
  }
}

function emptyPersisted(): CommunityGamePersistedState {
  return {
    totalXp: 0,
    lifetimeSightings: 0,
    questWeekKey: '',
    weeklySightings: 0,
    weeklyGpsSightings: 0,
    weeklyExtraSightings: 0,
    weeksWithUpload: [],
    gpsHintTotal: 0,
    manualHintTotal: 0,
    sightingsWithExtraPhotos: 0,
    trainingCompleted: false,
    badges: [],
    completedWeeklyQuestIds: [],
  };
}

/** Merge guest progress into user profile on first login (additive stats, union badges). */
export function mergeGuestIntoUser(
  user: CommunityGamePersistedState | null,
  guest: CommunityGamePersistedState | null,
): CommunityGamePersistedState {
  if (!guest || guest.lifetimeSightings === 0) return user ?? emptyPersisted();
  if (!user || user.lifetimeSightings === 0) {
    return { ...emptyPersisted(), ...guest };
  }
  const badges = Array.from(new Set([...user.badges, ...guest.badges]));
  const weeks = Array.from(new Set([...user.weeksWithUpload, ...guest.weeksWithUpload])).slice(-60);
  return {
    totalXp: user.totalXp + guest.totalXp,
    lifetimeSightings: user.lifetimeSightings + guest.lifetimeSightings,
    questWeekKey: user.questWeekKey || guest.questWeekKey,
    weeklySightings: user.weeklySightings,
    weeklyGpsSightings: user.weeklyGpsSightings,
    weeklyExtraSightings: user.weeklyExtraSightings,
    weeksWithUpload: weeks,
    gpsHintTotal: user.gpsHintTotal + guest.gpsHintTotal,
    manualHintTotal: user.manualHintTotal + guest.manualHintTotal,
    sightingsWithExtraPhotos: user.sightingsWithExtraPhotos + guest.sightingsWithExtraPhotos,
    trainingCompleted: user.trainingCompleted || guest.trainingCompleted,
    badges,
    completedWeeklyQuestIds: user.completedWeeklyQuestIds,
  };
}
