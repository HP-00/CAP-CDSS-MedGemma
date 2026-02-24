import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useTheme } from "@/components/theme-provider";
import { useBatchContext } from "@/stores/batch-store";

export function Header() {
  const { theme, setTheme } = useTheme();
  const { patients, activePatientId, setActivePatient } = useBatchContext();

  const [allRead, setAllRead] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  const activePatient = activePatientId
    ? patients.find((p) => p.caseId === activePatientId)
    : null;

  return (
    <header className="sticky top-0 z-50 border-b border-border/50 bg-background/80 backdrop-blur-md">
      <div className="flex h-12 items-center justify-between px-5">
        {/* Left: Ward name */}
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold tracking-tight">Respiratory Ward 11A</span>
          <Badge variant="outline" className="text-[10px] font-mono border-border/50 text-muted-foreground">
            MedGemma 4B
          </Badge>

          {/* Active patient indicator */}
          {activePatient && (
            <div className="flex items-center gap-2 ml-1">
              <div className="h-4 w-px bg-border/60" />
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-clinical-teal opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-clinical-teal" />
              </span>
              <span className="text-xs font-medium text-foreground">{activePatient.name}</span>
              <span className="text-[10px] text-muted-foreground">
                {activePatient.age}{activePatient.sex?.[0]} &middot; {activePatient.bed}
              </span>
              <button
                onClick={() => setActivePatient(null)}
                className="inline-flex h-4 w-4 items-center justify-center rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
                aria-label="Deselect patient"
              >
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                  <path d="M18 6 6 18" /><path d="m6 6 12 12" />
                </svg>
              </button>
            </div>
          )}
        </div>

        {/* Right */}
        <div className="flex items-center gap-2.5">
          <Badge variant="outline" className="text-[10px] border-severity-moderate/30 text-severity-moderate hidden sm:inline-flex">
            AI-generated outputs · For demonstration only — not validated for clinical use
          </Badge>

          {/* Message inbox (cosmetic) */}
          <DropdownMenu>
            <DropdownMenuTrigger className="relative inline-flex h-8 w-8 items-center justify-center rounded-md border border-border/50 bg-background hover:bg-accent transition-colors">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect width="20" height="16" x="2" y="4" rx="2" />
                <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
              </svg>
              {!allRead && (
                <span className="absolute -top-1 -right-1 h-4 w-4 rounded-full bg-severity-high text-[9px] text-white flex items-center justify-center font-bold">
                  3
                </span>
              )}
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-80 p-0">
              <div className="flex items-center justify-between px-3 py-2 border-b border-border/50">
                <span className="text-xs font-semibold">Inbox</span>
                <button onClick={() => setAllRead(true)} className="text-[10px] text-muted-foreground hover:text-foreground transition-colors">Mark all as read</button>
              </div>
              {[
                { initials: "MG", color: "bg-clinical-cyan/20 text-clinical-cyan", sender: "MedGemma", time: "1m ago", msg: "I don't need coffee. But I understand why you do.", unread: true },
                { initials: "IT", color: "bg-severity-high/15 text-severity-high", sender: "IT Helpdesk", time: "15m ago", msg: "Mandatory password change. Your new password must contain a Greek letter and an emoji.", unread: true },
                { initials: "AK", color: "bg-purple-500/15 text-purple-500", sender: "Dr. Khan", time: "1h ago", msg: "Night team left 6 outstanding jobs. They described them as 'minor'. They are not minor.", unread: true },
                { initials: "BM", color: "bg-severity-moderate/15 text-severity-moderate", sender: "Bed Manager", time: "2h ago", msg: "Ward 11A has 0 beds. Ward 11B also has 0 beds. Good luck.", unread: false },
                { initials: "HR", color: "bg-muted text-muted-foreground", sender: "HR", time: "6h ago", msg: "Your annual leave request has been received and will be ignored shortly.", unread: false },
              ].map((m, i) => {
                const isUnread = m.unread && !allRead;
                return (
                  <div key={i} className="flex gap-2.5 px-3 py-2.5 hover:bg-accent/50 transition-colors cursor-default border-b border-border/30 last:border-b-0">
                    <Avatar className="h-7 w-7 shrink-0 mt-0.5">
                      <AvatarFallback className={`${m.color} text-[9px] font-semibold`}>{m.initials}</AvatarFallback>
                    </Avatar>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <span className={`text-[11px] font-medium ${isUnread ? "text-foreground" : "text-muted-foreground"}`}>{m.sender}</span>
                        <span className="text-[10px] text-muted-foreground shrink-0">{m.time}</span>
                      </div>
                      <p className={`text-[11px] leading-relaxed mt-0.5 ${isUnread ? "text-foreground/80" : "text-muted-foreground"}`}>{m.msg}</p>
                    </div>
                    {isUnread && <span className="h-1.5 w-1.5 rounded-full bg-clinical-cyan shrink-0 mt-2" />}
                  </div>
                );
              })}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Theme toggle */}
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-border/50 bg-background hover:bg-accent transition-colors"
            aria-label="Toggle theme"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="hidden dark:block">
              <circle cx="12" cy="12" r="4" />
              <path d="M12 2v2" /><path d="M12 20v2" />
              <path d="m4.93 4.93 1.41 1.41" /><path d="m17.66 17.66 1.41 1.41" />
              <path d="M2 12h2" /><path d="M20 12h2" />
              <path d="m6.34 17.66-1.41 1.41" /><path d="m19.07 4.93-1.41 1.41" />
            </svg>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="block dark:hidden">
              <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
            </svg>
          </button>

          {/* Doctor avatar + dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger className="flex items-center gap-2 hover:bg-accent rounded-md px-2 py-1 transition-colors">
              <Avatar className="h-7 w-7">
                <AvatarFallback className="bg-clinical-cyan/20 text-clinical-cyan text-[11px] font-semibold">
                  JS
                </AvatarFallback>
              </Avatar>
              <span className="text-xs font-medium hidden md:inline">Dr. James Smith</span>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="text-muted-foreground">
                <path d="m6 9 6 6 6-6" />
              </svg>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem className="text-xs" onSelect={() => setProfileOpen(true)}>My Profile</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="text-xs text-severity-high">Sign Out</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
      {/* Profile modal */}
      <Dialog open={profileOpen} onOpenChange={setProfileOpen}>
        <DialogContent className="sm:max-w-sm p-0 gap-0 overflow-hidden">
          <DialogHeader className="px-5 pt-5 pb-4 border-b border-border/50">
            <div className="flex items-center gap-3">
              <Avatar className="h-12 w-12">
                <AvatarFallback className="bg-clinical-cyan/20 text-clinical-cyan text-base font-semibold">JS</AvatarFallback>
              </Avatar>
              <div>
                <DialogTitle className="text-sm font-semibold">Dr. James Smith</DialogTitle>
                <p className="text-xs text-muted-foreground mt-0.5">FY2 — Respiratory Medicine</p>
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-[10px] text-muted-foreground">GMC: 7654321</span>
                  <span className="text-[10px] text-muted-foreground">Bleep: 2471</span>
                </div>
              </div>
            </div>
          </DialogHeader>
          <div className="px-5 py-4">
            <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-3">Today's Stats</p>
            <div className="space-y-2">
              {[
                ["Hours on shift", "11"],
                ["Coffees consumed", "4"],
                ["Bloods chased", "11"],
                ["Times bleeped", "14"],
                ["Meals eaten", "0"],
                ["Discharge summaries written", "0"],
                ["Referrals attempted", "3"],
                ["Referrals accepted", "0"],
                ["Morale", "Low"],
              ].map(([label, value]) => (
                <div key={label} className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">{label}</span>
                  <span className={`text-xs font-medium ${value === "0" || value === "Low" ? "text-severity-high" : "text-foreground"}`}>{value}</span>
                </div>
              ))}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </header>
  );
}
