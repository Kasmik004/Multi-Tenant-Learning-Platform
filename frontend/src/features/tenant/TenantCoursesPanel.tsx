"use client";

import { useCallback, useEffect, useState } from "react";
import { useApiClient } from "@/hooks/useApiClient";
import type { Schemas } from "@/lib/api/client";

type CourseRead = Schemas["CourseRead"];
type UserRead = Schemas["UserRead"];
type EnrollmentRead = Schemas["EnrollmentRead"];

export function TenantCoursesPanel() {
  const api = useApiClient();
  const [courses, setCourses] = useState<CourseRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newPublished, setNewPublished] = useState(false);
  const [createBusy, setCreateBusy] = useState(false);

  // Enrollment modal state
  const [selectedCourse, setSelectedCourse] = useState<CourseRead | null>(null);
  const [enrollments, setEnrollments] = useState<EnrollmentRead[]>([]);
  const [allUsers, setAllUsers] = useState<UserRead[]>([]);
  const [enrollLoading, setEnrollLoading] = useState(false);
  const [assignUserId, setAssignUserId] = useState("");
  const [assignBusy, setAssignBusy] = useState(false);

  const fetchCourses = useCallback(async () => {
    const { data, error } = await api.GET("/api/v1/courses");
    if (error) setError("Failed to load courses");
    else if (data) {
      setCourses(data.items);
      setError("");
    }
    setLoading(false);
  }, [api]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchCourses();
  }, [fetchCourses]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreateBusy(true);
    const { data } = await api.POST("/api/v1/courses", {
      body: { title: newTitle, description: newDesc, is_published: newPublished },
    });
    setCreateBusy(false);
    if (data) {
      setShowCreate(false);
      setNewTitle("");
      setNewDesc("");
      setNewPublished(false);
      fetchCourses();
    }
  }

  async function handleTogglePublish(course: CourseRead) {
    const { data } = await api.PATCH("/api/v1/courses/{course_id}", {
      params: { path: { course_id: course.id } },
      body: { is_published: !course.is_published },
    });
    if (data) fetchCourses();
  }

  async function handleDelete(id: string) {
    if (!confirm("Permanently delete this course?")) return;
    const { error } = await api.DELETE("/api/v1/courses/{course_id}", {
      params: { path: { course_id: id } },
    });
    if (!error) fetchCourses();
  }

  // Enrollments
  async function openEnrollments(course: CourseRead) {
    setSelectedCourse(course);
    setEnrollLoading(true);
    const [enrRes, usersRes] = await Promise.all([
      api.GET("/api/v1/courses/{course_id}/enrollments", { params: { path: { course_id: course.id } } }),
      api.GET("/api/v1/users"),
    ]);
    if (enrRes.data) setEnrollments(enrRes.data.items);
    if (usersRes.data) setAllUsers(usersRes.data.items);
    setEnrollLoading(false);
  }

  async function handleAssign(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedCourse || !assignUserId) return;
    setAssignBusy(true);
    const { data } = await api.POST("/api/v1/courses/{course_id}/enrollments", {
      params: { path: { course_id: selectedCourse.id } },
      body: { user_id: assignUserId },
    });
    setAssignBusy(false);
    if (data) {
      setAssignUserId("");
      openEnrollments(selectedCourse);
    }
  }

  async function handleUnassign(userId: string) {
    if (!selectedCourse) return;
    const { error } = await api.DELETE("/api/v1/courses/{course_id}/enrollments/{user_id}", {
      params: { path: { course_id: selectedCourse.id, user_id: userId } },
    });
    if (!error) openEnrollments(selectedCourse);
  }

  // Filter users not already enrolled
  const enrolledUserIds = new Set(enrollments.map(e => e.user_id));
  const assignableUsers = allUsers.filter(u => !enrolledUserIds.has(u.id));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Courses</h2>
        {!showCreate && (
          <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
            + New Course
          </button>
        )}
      </div>

      {showCreate && (
        <form onSubmit={handleCreate} className="card space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">Create Course</h3>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setShowCreate(false)}>Cancel</button>
          </div>
          <div>
            <label className="label">Title</label>
            <input className="input" value={newTitle} onChange={e => setNewTitle(e.target.value)} required />
          </div>
          <div>
            <label className="label">Description</label>
            <textarea className="input" value={newDesc} onChange={e => setNewDesc(e.target.value)} rows={3} />
          </div>
          <div className="flex items-center gap-2">
            <input type="checkbox" id="pub" checked={newPublished} onChange={e => setNewPublished(e.target.checked)} />
            <label htmlFor="pub" className="text-sm font-medium">Publish immediately</label>
          </div>
          <button type="submit" className="btn btn-primary" disabled={createBusy}>Create</button>
        </form>
      )}

      {error && <div className="alert-error">{error}</div>}

      {loading ? (
        <div className="flex justify-center p-8"><span className="spinner spinner-lg" /></div>
      ) : courses.length === 0 ? (
        <div className="empty-state card">No courses found.</div>
      ) : (
        <div className="card overflow-hidden !p-0">
          <table className="data-table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Status</th>
                <th>Created</th>
                <th className="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {courses.map(c => (
                <tr key={c.id}>
                  <td>
                    <div className="font-medium">{c.title}</div>
                    <div className="text-xs text-[var(--muted)] truncate max-w-xs">{c.description}</div>
                  </td>
                  <td>
                    <button className={`badge cursor-pointer ${c.is_published ? "badge-success" : "badge-neutral"}`} onClick={() => handleTogglePublish(c)}>
                      {c.is_published ? "Published" : "Draft"}
                    </button>
                  </td>
                  <td className="text-xs">{new Date(c.created_at).toLocaleDateString()}</td>
                  <td className="text-right space-x-2">
                    <button className="btn btn-ghost btn-sm" onClick={() => openEnrollments(c)}>Manage Enrollments</button>
                    <button className="btn btn-ghost btn-sm text-red-500" onClick={() => handleDelete(c.id)}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selectedCourse && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setSelectedCourse(null)}>
          <div className="modal flex max-h-[90vh] max-w-2xl flex-col">
            <div className="flex items-center justify-between mb-4">
              <h3 className="mb-0 text-lg font-semibold text-wrap">{selectedCourse.title} - Enrollments</h3>
              <button className="btn btn-ghost btn-sm" onClick={() => setSelectedCourse(null)}>Close</button>
            </div>
            
            <form onSubmit={handleAssign} className="flex gap-2 mb-6">
              <select className="input" value={assignUserId} onChange={e => setAssignUserId(e.target.value)} required>
                <option value="">Select a user to assign...</option>
                {assignableUsers.map(u => <option key={u.id} value={u.id}>{u.full_name} ({u.email})</option>)}
              </select>
              <button type="submit" className="btn btn-primary shrink-0" disabled={assignBusy || !assignUserId}>Assign</button>
            </form>

            <div className="overflow-y-auto">
              {enrollLoading ? (
                <div className="flex justify-center p-8"><span className="spinner" /></div>
              ) : enrollments.length === 0 ? (
                <div className="empty-state text-sm py-4">No users assigned.</div>
              ) : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>User</th>
                      <th>Status</th>
                      <th>Progress</th>
                      <th className="text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {enrollments.map(enr => {
                      const u = allUsers.find(u => u.id === enr.user_id);
                      return (
                        <tr key={enr.id}>
                          <td>
                            <div className="font-medium">{u?.full_name || "Unknown"}</div>
                            <div className="text-xs text-[var(--muted)]">{u?.email}</div>
                          </td>
                          <td>
                            <span className={`badge ${enr.status === "completed" ? "badge-success" : enr.status === "in_progress" ? "badge-info" : "badge-neutral"}`}>
                              {enr.status.replace("_", " ")}
                            </span>
                          </td>
                          <td className="w-32">
                            <div className="text-xs font-medium text-right mb-1">{enr.progress_percent}%</div>
                            <div className="progress-bar"><div className="progress-fill" style={{ width: `${enr.progress_percent}%` }} /></div>
                          </td>
                          <td className="text-right">
                            <button className="btn btn-ghost btn-sm text-red-500" onClick={() => handleUnassign(enr.user_id)}>Unassign</button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
