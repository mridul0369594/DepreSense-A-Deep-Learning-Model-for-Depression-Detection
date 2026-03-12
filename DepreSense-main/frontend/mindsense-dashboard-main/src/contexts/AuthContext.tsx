import { createContext, useContext, useState, ReactNode, useCallback } from "react";

type UserRole = "clinician" | "admin" | null;

interface UserInfo {
  name: string;
  email: string;
}

/** Fields that can be updated from the Settings page */
export interface ProfileUpdate {
  firstName?: string;
  lastName?: string;
  phone?: string;
  photo?: string; // base64 data-URL
}

interface AuthContextType {
  isAuthenticated: boolean;
  role: UserRole;
  clinicianId: string;
  userName: string;
  userEmail: string;
  userPhone: string;
  userPhoto: string; // base64 data-URL or ""
  login: (role: UserRole, user?: UserInfo) => void;
  logout: () => void;
  /** Update profile fields and persist to localStorage */
  updateProfile: (updates: ProfileUpdate) => void;
}

const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  role: null,
  clinicianId: "",
  userName: "",
  userEmail: "",
  userPhone: "",
  userPhoto: "",
  login: () => { },
  logout: () => { },
  updateProfile: () => { },
});

export const useAuth = () => useContext(AuthContext);

/**
 * Restore auth state from localStorage so page refresh / direct navigation
 * doesn't lose the user's session.
 */
function getInitialAuth() {
  const token = localStorage.getItem("token");
  const savedRole = localStorage.getItem("role") as UserRole;
  return {
    isAuthenticated: !!token,
    role: token ? savedRole : null,
  };
}

function getInitialClinicianId() {
  const saved = localStorage.getItem("clinicianId");
  if (saved) return saved;
  const id = `CLN-${Math.floor(Math.random() * 9000) + 1000}`;
  localStorage.setItem("clinicianId", id);
  return id;
}

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const initial = getInitialAuth();
  const [isAuthenticated, setIsAuthenticated] = useState(initial.isAuthenticated);
  const [role, setRole] = useState<UserRole>(initial.role);
  const [clinicianId] = useState(getInitialClinicianId);
  const [userName, setUserName] = useState(localStorage.getItem("userName") || "");
  const [userEmail, setUserEmail] = useState(localStorage.getItem("userEmail") || "");
  const [userPhone, setUserPhone] = useState(localStorage.getItem("userPhone") || "");
  const [userPhoto, setUserPhoto] = useState(localStorage.getItem("userPhoto") || "");

  const login = (userRole: UserRole, user?: UserInfo) => {
    setIsAuthenticated(true);
    setRole(userRole);
    localStorage.setItem("role", userRole ?? "");

    if (user) {
      setUserName(user.name);
      setUserEmail(user.email);
      localStorage.setItem("userName", user.name);
      localStorage.setItem("userEmail", user.email);
    }
  };

  const logout = () => {
    setIsAuthenticated(false);
    setRole(null);
    setUserName("");
    setUserEmail("");
    setUserPhone("");
    setUserPhoto("");
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    localStorage.removeItem("clinicianId");
    localStorage.removeItem("lastPredictionId");
    localStorage.removeItem("userName");
    localStorage.removeItem("userEmail");
    localStorage.removeItem("userPhone");
    localStorage.removeItem("userPhoto");
  };

  /**
   * Update profile fields from the Settings page.
   * Recombines firstName + lastName into the full `userName`.
   */
  const updateProfile = useCallback((updates: ProfileUpdate) => {
    if (updates.firstName !== undefined || updates.lastName !== undefined) {
      // We need the current parts to merge partial updates
      const parts = userName.split(" ");
      const currentFirst = parts[0] || "";
      const currentLast = parts.slice(1).join(" ") || "";

      const newFirst = updates.firstName !== undefined ? updates.firstName : currentFirst;
      const newLast = updates.lastName !== undefined ? updates.lastName : currentLast;
      const fullName = `${newFirst} ${newLast}`.trim();

      setUserName(fullName);
      localStorage.setItem("userName", fullName);
    }

    if (updates.phone !== undefined) {
      setUserPhone(updates.phone);
      localStorage.setItem("userPhone", updates.phone);
    }

    if (updates.photo !== undefined) {
      setUserPhoto(updates.photo);
      localStorage.setItem("userPhoto", updates.photo);
    }
  }, [userName]);

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        role,
        clinicianId,
        userName,
        userEmail,
        userPhone,
        userPhoto,
        login,
        logout,
        updateProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
