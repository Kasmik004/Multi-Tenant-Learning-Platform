"use client";

import { useCallback, useEffect, useState } from "react";
import { DashboardShell } from "@/components/ui/DashboardShell";
import { useApiClient } from "@/hooks/useApiClient";
import type { Schemas } from "@/lib/api/client";

type EnrollmentRead = Schemas["EnrollmentRead"];
type CourseRead = Schemas["CourseRead"];

const NAV_ITEMS = [
  { id: "my-courses", label: "My Courses" },
];

export function LearnerDashboard() {
  const [activeSection, setActiveSection] = useState("my-courses");
  const api = useApiClient();
  
  const [enrollments, setEnrollments] = useState<EnrollmentRead[]>([]);
  const [courses, setCourses] = useState<Record<string, CourseRead>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const fetchMyCourses = useCallback(async () => {
    const { data: enrData, error: enrErr } = await api.GET("/api/v1/enrollments/me");
    if (enrErr) {
      setError("Failed to load your courses. Your organization's trial may have expired.");
      setLoading(false);
      return;
    }
    
    if (enrData) {
      setEnrollments(enrData.items);
      
      // Fetch details for each course. In a real app we'd have a batch endpoint or include it in enrollments.
      const courseMap: Record<string, CourseRead> = {};
      await Promise.all(
        enrData.items.map(async (enr) => {
          const { data: courseData } = await api.GET("/api/v1/courses/{course_id}", {
            params: { path: { course_id: enr.course_id } }
          });
          if (courseData) {
            courseMap[courseData.id] = courseData;
          }
        })
      );
      setCourses(courseMap);
    }
    setLoading(false);
  }, [api]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchMyCourses();
  }, [fetchMyCourses]);

  async function updateProgress(courseId: string, newPercent: number) {
    setUpdatingId(courseId);
    const { data } = await api.PUT("/api/v1/courses/{course_id}/progress", {
      params: { path: { course_id: courseId } },
      body: { progress_percent: newPercent }
    });
    setUpdatingId(null);
    if (data) {
      // Update local state without refetching everything
      setEnrollments(prev => prev.map(e => e.course_id === courseId ? data : e));
    }
  }

  return (
    <DashboardShell
      title="Learner Dashboard"
      navItems={NAV_ITEMS}
      activeItem={activeSection}
      onNavigate={setActiveSection}
    >
      <div className="space-y-6 max-w-4xl mx-auto">
        <h2 className="text-xl font-semibold">My Learning Path</h2>
        
        {error && <div className="alert-error">{error}</div>}
        
        {loading ? (
          <div className="flex justify-center p-8"><span className="spinner spinner-lg" /></div>
        ) : enrollments.length === 0 ? (
          <div className="empty-state card">You are not enrolled in any courses yet.</div>
        ) : (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            {enrollments.map((enr) => {
              const course = courses[enr.course_id];
              return (
                <div key={enr.id} className="card flex flex-col space-y-4">
                  <div>
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="font-semibold text-lg">{course?.title || "Loading..."}</h3>
                      <span className={`badge shrink-0 ${enr.status === "completed" ? "badge-success" : enr.status === "in_progress" ? "badge-info" : "badge-neutral"}`}>
                        {enr.status.replace("_", " ")}
                      </span>
                    </div>
                    <p className="text-sm text-[var(--muted)] line-clamp-2 min-h-[2.5rem]">
                      {course?.description || "No description provided."}
                    </p>
                  </div>
                  
                  <div className="mt-auto pt-4 border-t border-[var(--card-border)] space-y-3">
                    <div className="flex justify-between text-sm">
                      <span className="font-medium text-[var(--muted)]">Progress</span>
                      <span className="font-bold">{enr.progress_percent}%</span>
                    </div>
                    <div className="progress-bar">
                      <div className="progress-fill" style={{ width: `${enr.progress_percent}%` }} />
                    </div>
                    
                    <div className="flex gap-2 pt-2">
                      <button 
                        className="btn btn-ghost flex-1"
                        disabled={updatingId === enr.course_id || enr.progress_percent <= 0}
                        onClick={() => updateProgress(enr.course_id, Math.max(0, enr.progress_percent - 10))}
                      >
                        -10%
                      </button>
                      <button 
                        className="btn btn-primary flex-1"
                        disabled={updatingId === enr.course_id || enr.progress_percent >= 100}
                        onClick={() => updateProgress(enr.course_id, Math.min(100, enr.progress_percent + 20))}
                      >
                        {enr.progress_percent === 100 ? "Done" : "Learn"} (+20%)
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </DashboardShell>
  );
}
