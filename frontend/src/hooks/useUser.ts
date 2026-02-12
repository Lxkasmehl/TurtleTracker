import { useAppSelector, useAppDispatch } from '../store/hooks';
import { setRole, setIsLoggedIn, login, logout, setUser, type UserInfo } from '../store/slices/userSlice';
import { type UserRole } from '../types/User';

export function useUser() {
  const dispatch = useAppDispatch();
  const { role, isLoggedIn, user, authChecked } = useAppSelector((state) => state.user);

  return {
    role,
    isLoggedIn,
    user,
    authChecked,
    setRole: (newRole: UserRole) => dispatch(setRole(newRole)),
    setIsLoggedIn: (loggedIn: boolean) => dispatch(setIsLoggedIn(loggedIn)),
    setUser: (userInfo: UserInfo) => dispatch(setUser(userInfo)),
    login: (userInfo: UserInfo) => dispatch(login(userInfo)),
    logout: () => dispatch(logout()),
  };
}
