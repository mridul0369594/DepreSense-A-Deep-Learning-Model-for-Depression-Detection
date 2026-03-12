import { createContext, useContext, useState, ReactNode, useEffect, useCallback } from "react";
import type { PredictionResponse } from "@/lib/api";

interface BDIResult {
  score: number;
  severity: "Minimal" | "Mild" | "Moderate" | "Severe";
  completedAt: string;
}

interface MDDResult {
  /** Real prediction data from the backend */
  prediction: PredictionResponse;
  patientId: string;
  fileName: string;
  analysedAt: string;
}

export interface PatientRecord {
  patientName: string;
  patientId: string;
  createdAt: string;
}

// ── Patient Session History ────────────────────────────────
export interface PatientSessionRecord {
  patientId: string;
  patientName: string;
  sessionDate: string;   // "YYYY-MM-DD"
  sessionTime: string;   // "HH:MM AM/PM"
  bdiScore: number | null;
  bdiSeverity: string | null;
  mddResult: string | null;
}

interface SessionContextType {
  bdiResult: BDIResult | null;
  setBdiResult: (result: BDIResult | null) => void;
  mddResult: MDDResult | null;
  setMddResult: (result: MDDResult | null) => void;
  currentPatientId: string | null;
  setCurrentPatientId: (id: string | null) => void;
  currentPatientName: string | null;
  setCurrentPatientName: (name: string | null) => void;
  patients: PatientRecord[];
  addPatient: (record: PatientRecord) => void;
  /** Legacy — kept for backward compat; returns just the IDs */
  patientIds: string[];
  /** Legacy — kept for backward compat */
  addPatientId: (id: string) => void;
  /** Patient session history records */
  patientSessions: PatientSessionRecord[];
  /** Create or update a session record after BDI completion */
  addBdiSession: (data: {
    patientId: string;
    patientName: string;
    bdiScore: number;
    bdiSeverity: string;
  }) => void;
  /** Create or update a session record after MDD completion */
  addMddSession: (data: {
    patientId: string;
    patientName: string;
    mddResult: string;
  }) => void;
}

const PATIENTS_STORAGE_KEY = "depresense_patients";
const SESSIONS_STORAGE_KEY = "depresense_patient_sessions";

function loadPatients(): PatientRecord[] {
  try {
    const raw = localStorage.getItem(PATIENTS_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return parsed;
    }
  } catch {
    // ignore corrupt storage
  }
  return [];
}

function savePatients(patients: PatientRecord[]) {
  localStorage.setItem(PATIENTS_STORAGE_KEY, JSON.stringify(patients));
}

function loadSessions(): PatientSessionRecord[] {
  try {
    const raw = localStorage.getItem(SESSIONS_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return parsed;
    }
  } catch {
    // ignore corrupt storage
  }
  return [];
}

function saveSessions(sessions: PatientSessionRecord[]) {
  localStorage.setItem(SESSIONS_STORAGE_KEY, JSON.stringify(sessions));
}

/**
 * Returns the current date as "YYYY-MM-DD" and time as "HH:MM AM/PM".
 */
function getCurrentDateTime(): { date: string; time: string } {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  const date = `${year}-${month}-${day}`;

  let hours = now.getHours();
  const minutes = String(now.getMinutes()).padStart(2, "0");
  const ampm = hours >= 12 ? "PM" : "AM";
  hours = hours % 12 || 12;
  const time = `${String(hours).padStart(2, "0")}:${minutes} ${ampm}`;

  return { date, time };
}

const SessionContext = createContext<SessionContextType>({
  bdiResult: null,
  setBdiResult: () => { },
  mddResult: null,
  setMddResult: () => { },
  currentPatientId: null,
  setCurrentPatientId: () => { },
  currentPatientName: null,
  setCurrentPatientName: () => { },
  patients: [],
  addPatient: () => { },
  patientIds: [],
  addPatientId: () => { },
  patientSessions: [],
  addBdiSession: () => { },
  addMddSession: () => { },
});

export const useSession = () => useContext(SessionContext);

export const SessionProvider = ({ children }: { children: ReactNode }) => {
  const [bdiResult, setBdiResult] = useState<BDIResult | null>(null);
  const [mddResult, setMddResult] = useState<MDDResult | null>(null);
  const [currentPatientId, setCurrentPatientId] = useState<string | null>(null);
  const [currentPatientName, setCurrentPatientName] = useState<string | null>(null);
  const [patients, setPatients] = useState<PatientRecord[]>(loadPatients);
  const [patientSessions, setPatientSessions] = useState<PatientSessionRecord[]>(loadSessions);

  // Persist patients to localStorage whenever they change
  useEffect(() => {
    savePatients(patients);
  }, [patients]);

  // Persist sessions to localStorage whenever they change
  useEffect(() => {
    saveSessions(patientSessions);
  }, [patientSessions]);

  const addPatient = (record: PatientRecord) => {
    setPatients((prev) => {
      if (prev.some((p) => p.patientId === record.patientId)) return prev;
      return [...prev, record];
    });
  };

  // Legacy helpers — derived from the full patients list
  const patientIds = patients.map((p) => p.patientId);

  const addPatientId = (id: string) => {
    // No-op if patient already exists; for true new patients use addPatient
    if (!patients.some((p) => p.patientId === id)) {
      addPatient({ patientId: id, patientName: "", createdAt: new Date().toISOString() });
    }
  };

  // ── Session History Management ───────────────────────────

  /**
   * Find an existing session record for the same patient on the same date.
   * This enables merging BDI and MDD results into a single record.
   */
  const findExistingSessionIndex = useCallback(
    (sessions: PatientSessionRecord[], patientId: string, sessionDate: string): number => {
      return sessions.findIndex(
        (s) => s.patientId === patientId && s.sessionDate === sessionDate
      );
    },
    []
  );

  /**
   * Called when a BDI test completes.
   * Creates a new session record or updates an existing one for the same patient + date.
   */
  const addBdiSession = useCallback(
    (data: { patientId: string; patientName: string; bdiScore: number; bdiSeverity: string }) => {
      const { date, time } = getCurrentDateTime();

      setPatientSessions((prev) => {
        const existing = [...prev];
        const idx = findExistingSessionIndex(existing, data.patientId, date);

        if (idx !== -1) {
          // Update existing record — merge BDI data into it
          existing[idx] = {
            ...existing[idx],
            patientName: data.patientName,
            sessionTime: time,
            bdiScore: data.bdiScore,
            bdiSeverity: data.bdiSeverity,
          };
          return existing;
        }

        // Create new session record
        const newRecord: PatientSessionRecord = {
          patientId: data.patientId,
          patientName: data.patientName,
          sessionDate: date,
          sessionTime: time,
          bdiScore: data.bdiScore,
          bdiSeverity: data.bdiSeverity,
          mddResult: null,
        };
        return [...existing, newRecord];
      });
    },
    [findExistingSessionIndex]
  );

  /**
   * Called when MDD detection completes.
   * Creates a new session record or updates an existing one for the same patient + date.
   */
  const addMddSession = useCallback(
    (data: { patientId: string; patientName: string; mddResult: string }) => {
      const { date, time } = getCurrentDateTime();

      setPatientSessions((prev) => {
        const existing = [...prev];
        const idx = findExistingSessionIndex(existing, data.patientId, date);

        if (idx !== -1) {
          // Update existing record — merge MDD data into it
          existing[idx] = {
            ...existing[idx],
            patientName: data.patientName,
            sessionTime: time,
            mddResult: data.mddResult,
          };
          return existing;
        }

        // Create new session record
        const newRecord: PatientSessionRecord = {
          patientId: data.patientId,
          patientName: data.patientName,
          sessionDate: date,
          sessionTime: time,
          bdiScore: null,
          bdiSeverity: null,
          mddResult: data.mddResult,
        };
        return [...existing, newRecord];
      });
    },
    [findExistingSessionIndex]
  );

  return (
    <SessionContext.Provider
      value={{
        bdiResult,
        setBdiResult,
        mddResult,
        setMddResult,
        currentPatientId,
        setCurrentPatientId,
        currentPatientName,
        setCurrentPatientName,
        patients,
        addPatient,
        patientIds,
        addPatientId,
        patientSessions,
        addBdiSession,
        addMddSession,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
};
