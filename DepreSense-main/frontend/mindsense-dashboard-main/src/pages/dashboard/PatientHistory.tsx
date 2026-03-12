import { useState, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { History, Search, Eye, ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { useSession, type PatientSessionRecord } from "@/contexts/SessionContext";

const PatientHistory = () => {
  const { patientSessions } = useSession();
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("date-desc");
  const [selectedPatient, setSelectedPatient] = useState<PatientSessionRecord | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 5;

  // Filter and sort patients
  const filteredPatients = useMemo(() => {
    const filtered = patientSessions.filter(
      (session) =>
        session.patientId.toLowerCase().includes(searchQuery.toLowerCase()) ||
        session.patientName.toLowerCase().includes(searchQuery.toLowerCase())
    );

    return filtered.sort((a, b) => {
      switch (sortBy) {
        case "date-asc": {
          const dateCompare =
            new Date(a.sessionDate).getTime() - new Date(b.sessionDate).getTime();
          if (dateCompare !== 0) return dateCompare;
          // Same date — compare time
          return parseSessionTime(a.sessionTime) - parseSessionTime(b.sessionTime);
        }
        case "date-desc": {
          const dateCompare =
            new Date(b.sessionDate).getTime() - new Date(a.sessionDate).getTime();
          if (dateCompare !== 0) return dateCompare;
          // Same date — compare time (newest first)
          return parseSessionTime(b.sessionTime) - parseSessionTime(a.sessionTime);
        }
        case "id":
          return a.patientId.localeCompare(b.patientId);
        default:
          return 0;
      }
    });
  }, [patientSessions, searchQuery, sortBy]);

  // Reset to page 1 when search changes
  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
    setCurrentPage(1);
  };

  const totalPages = Math.ceil(filteredPatients.length / itemsPerPage);
  const paginatedPatients = filteredPatients.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  const getBDIColor = (level: string | null) => {
    switch (level) {
      case "Minimal":
        return "text-success bg-success/20";
      case "Mild":
        return "text-yellow-600 bg-yellow-100";
      case "Moderate":
        return "text-orange-600 bg-orange-100";
      case "Severe":
        return "text-destructive bg-destructive/20";
      default:
        return "text-muted-foreground bg-muted";
    }
  };

  const getMDDColor = (result: string | null) => {
    if (!result) return "text-muted-foreground bg-muted";
    if (result.includes("High")) return "bg-destructive/20 text-destructive";
    return "bg-success/20 text-success";
  };

  /** Format BDI Result column display */
  const formatBdiResult = (session: PatientSessionRecord) => {
    if (session.bdiScore !== null && session.bdiSeverity !== null) {
      return `${session.bdiScore} (${session.bdiSeverity})`;
    }
    return "Not Taken";
  };

  /** Format MDD Detection column display */
  const formatMddResult = (session: PatientSessionRecord) => {
    if (session.mddResult !== null) {
      return session.mddResult;
    }
    return "Not Performed";
  };

  /**
   * View Details: navigate to MDD results page with session data
   * so the system can retrieve the correct results.
   */
  const handleViewDetails = (session: PatientSessionRecord) => {
    setSelectedPatient(session);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Patient History</h1>
        <p className="text-muted-foreground">View and manage patient session records</p>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <CardTitle className="flex items-center gap-2">
              <History className="h-5 w-5 text-primary" />
              Session Records
            </CardTitle>
            <div className="flex flex-col gap-3 sm:flex-row">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  placeholder="Search by Patient ID or Name..."
                  value={searchQuery}
                  onChange={(e) => handleSearchChange(e.target.value)}
                  className="pl-9 sm:w-72"
                />
              </div>
              <Select value={sortBy} onValueChange={setSortBy}>
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="Sort by" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="date-desc">Newest First</SelectItem>
                  <SelectItem value="date-asc">Oldest First</SelectItem>
                  <SelectItem value="id">Patient ID</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Patient ID</TableHead>
                  <TableHead>Patient Name</TableHead>
                  <TableHead>Session Date</TableHead>
                  <TableHead>Time</TableHead>
                  <TableHead>BDI Result</TableHead>
                  <TableHead>MDD Detection</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedPatients.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground">
                      No records found
                    </TableCell>
                  </TableRow>
                ) : (
                  paginatedPatients.map((session, index) => (
                    <TableRow key={`${session.patientId}-${session.sessionDate}-${index}`}>
                      <TableCell className="font-medium">{session.patientId}</TableCell>
                      <TableCell>{session.patientName || "—"}</TableCell>
                      <TableCell>{session.sessionDate}</TableCell>
                      <TableCell>{session.sessionTime}</TableCell>
                      <TableCell>
                        <span
                          className={cn(
                            "inline-flex rounded-full px-2 py-1 text-xs font-medium",
                            session.bdiScore !== null
                              ? getBDIColor(session.bdiSeverity)
                              : "text-muted-foreground bg-muted"
                          )}
                        >
                          {formatBdiResult(session)}
                        </span>
                      </TableCell>
                      <TableCell>
                        <span
                          className={cn(
                            "inline-flex rounded-full px-2 py-1 text-xs font-medium",
                            getMDDColor(session.mddResult)
                          )}
                        >
                          {formatMddResult(session)}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleViewDetails(session)}
                        >
                          <Eye className="mr-2 h-4 w-4" />
                          View Details
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-4 flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Showing {(currentPage - 1) * itemsPerPage + 1} to{" "}
                {Math.min(currentPage * itemsPerPage, filteredPatients.length)} of{" "}
                {filteredPatients.length} records
              </p>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <span className="text-sm">
                  Page {currentPage} of {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Patient Details Modal */}
      <Dialog open={!!selectedPatient} onOpenChange={() => setSelectedPatient(null)}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Patient Details - {selectedPatient?.patientId}</DialogTitle>
          </DialogHeader>
          {selectedPatient && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="rounded-lg bg-muted/50 p-3">
                  <p className="text-xs text-muted-foreground">Patient Name</p>
                  <p className="font-medium">{selectedPatient.patientName || "—"}</p>
                </div>
                <div className="rounded-lg bg-muted/50 p-3">
                  <p className="text-xs text-muted-foreground">Patient ID</p>
                  <p className="font-medium">{selectedPatient.patientId}</p>
                </div>
                <div className="rounded-lg bg-muted/50 p-3">
                  <p className="text-xs text-muted-foreground">Session Date</p>
                  <p className="font-medium">{selectedPatient.sessionDate}</p>
                </div>
                <div className="rounded-lg bg-muted/50 p-3">
                  <p className="text-xs text-muted-foreground">Session Time</p>
                  <p className="font-medium">{selectedPatient.sessionTime}</p>
                </div>
              </div>

              <div className="rounded-lg border p-4">
                <h4 className="mb-3 font-semibold">BDI Assessment</h4>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Score</span>
                  <span
                    className={cn(
                      "rounded-full px-3 py-1 text-sm font-medium",
                      selectedPatient.bdiScore !== null
                        ? getBDIColor(selectedPatient.bdiSeverity)
                        : "text-muted-foreground bg-muted"
                    )}
                  >
                    {selectedPatient.bdiScore !== null
                      ? `${selectedPatient.bdiScore} - ${selectedPatient.bdiSeverity}`
                      : "Not Taken"}
                  </span>
                </div>
              </div>

              <div className="rounded-lg border p-4">
                <h4 className="mb-3 font-semibold">MDD Detection</h4>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Result</span>
                  <span
                    className={cn(
                      "rounded-full px-3 py-1 text-sm font-medium",
                      getMDDColor(selectedPatient.mddResult)
                    )}
                  >
                    {selectedPatient.mddResult || "Not Performed"}
                  </span>
                </div>
              </div>

              <div className="flex justify-end">
                <Button variant="outline" onClick={() => setSelectedPatient(null)}>
                  Close
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

/**
 * Parse session time string (e.g. "02:15 PM") into minutes-since-midnight
 * for sorting purposes.
 */
function parseSessionTime(timeStr: string): number {
  try {
    const [timePart, ampm] = timeStr.split(" ");
    const [hoursStr, minutesStr] = timePart.split(":");
    let hours = parseInt(hoursStr, 10);
    const minutes = parseInt(minutesStr, 10);
    if (ampm?.toUpperCase() === "PM" && hours !== 12) hours += 12;
    if (ampm?.toUpperCase() === "AM" && hours === 12) hours = 0;
    return hours * 60 + minutes;
  } catch {
    return 0;
  }
}

export default PatientHistory;
