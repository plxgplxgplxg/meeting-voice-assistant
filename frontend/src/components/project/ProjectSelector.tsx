"use client";

import React, { useEffect, useState } from "react";
import { Folder, ChevronDown, Plus, Users, X, Check, Shield } from "lucide-react";
import { fetchApi } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export interface Project {
  id: string;
  name: string;
  description: string | null;
  owner_id: string;
  created_at: string;
}

interface ProjectSelectorProps {
  selectedProjectId: string | null;
  onSelectProject: (projectId: string | null, project: Project | null) => void;
}

export function ProjectSelector({
  selectedProjectId,
  onSelectProject,
}: ProjectSelectorProps) {
  const { user } = useAuth();
  const [projects, setProjects] = useState<Project[]>([]);
  const [isOpen, setIsOpen] = useState(false);

  // Create Project Modal
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [newProjectDesc, setNewProjectDesc] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchProjects = async () => {
    if (!user) return;
    try {
      const data = await fetchApi<Project[]>("/projects");
      setProjects(data);
    } catch {
      setProjects([]);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, [user]);

  const selectedProject = projects.find((p) => p.id === selectedProjectId) || null;

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjectName.trim()) return;

    setIsSubmitting(true);
    try {
      const created = await fetchApi<Project>("/projects", {
        method: "POST",
        body: JSON.stringify({
          name: newProjectName.trim(),
          description: newProjectDesc.trim() || null,
        }),
      });
      setProjects((prev) => [created, ...prev]);
      onSelectProject(created.id, created);
      setIsCreateOpen(false);
      setNewProjectName("");
      setNewProjectDesc("");
    } catch (err: any) {
      alert(err.message || "Không thể tạo dự án.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!user) return null;

  return (
    <>
      <div className="relative">
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50 transition text-xs font-semibold text-slate-800 shadow-sm"
        >
          <Folder className="w-3.5 h-3.5 text-slate-500" />
          <span className="max-w-[140px] truncate">
            {selectedProject ? selectedProject.name : "Tất Cả Cuộc Họp"}
          </span>
          <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
        </button>

        {isOpen && (
          <div className="absolute left-0 mt-1.5 w-60 rounded-xl bg-white border border-slate-200 shadow-lg py-1.5 z-30 animate-in fade-in">
            <button
              onClick={() => {
                onSelectProject(null, null);
                setIsOpen(false);
              }}
              className={`w-full px-3 py-2 text-left text-xs font-medium flex items-center justify-between hover:bg-slate-50 transition ${
                selectedProjectId === null
                  ? "text-emerald-700 bg-emerald-50/50 font-bold"
                  : "text-slate-700"
              }`}
            >
              <span>Tất Cả Cuộc Họp</span>
              {selectedProjectId === null && (
                <Check className="w-3.5 h-3.5 text-emerald-600" />
              )}
            </button>

            <div className="my-1 border-t border-slate-100" />

            <div className="max-h-48 overflow-y-auto">
              {projects.map((p) => (
                <button
                  key={p.id}
                  onClick={() => {
                    onSelectProject(p.id, p);
                    setIsOpen(false);
                  }}
                  className={`w-full px-3 py-2 text-left text-xs font-medium flex items-center justify-between hover:bg-slate-50 transition ${
                    selectedProjectId === p.id
                      ? "text-emerald-700 bg-emerald-50/50 font-bold"
                      : "text-slate-700"
                  }`}
                >
                  <span className="truncate">{p.name}</span>
                  {selectedProjectId === p.id && (
                    <Check className="w-3.5 h-3.5 text-emerald-600" />
                  )}
                </button>
              ))}
            </div>

            <div className="my-1 border-t border-slate-100" />

            <button
              onClick={() => {
                setIsOpen(false);
                setIsCreateOpen(true);
              }}
              className="w-full px-3 py-2 text-left text-xs font-semibold text-slate-900 hover:bg-slate-50 transition flex items-center gap-2"
            >
              <Plus className="w-3.5 h-3.5 text-emerald-600" />
              <span>Tạo Dự Án Mới</span>
            </button>
          </div>
        )}
      </div>

      {/* Modal: Create Project */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-in fade-in">
          <div className="bg-white rounded-2xl max-w-md w-full border border-slate-200 shadow-xl p-6">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <h3 className="text-base font-bold text-slate-900">
                Khởi Tạo Dự Án Mới
              </h3>
              <button
                onClick={() => setIsCreateOpen(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateProject} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Tên Dự Án
                </label>
                <input
                  type="text"
                  required
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  placeholder="Ví dụ: Đồ Án Tốt Nghiệp 2024"
                  className="w-full px-3.5 py-2 text-sm bg-white border border-slate-300 rounded-xl text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-600/20 focus:border-emerald-600"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Mô Tả (Tùy chọn)
                </label>
                <textarea
                  rows={2}
                  value={newProjectDesc}
                  onChange={(e) => setNewProjectDesc(e.target.value)}
                  placeholder="Mô tả mục tiêu và nhóm làm việc..."
                  className="w-full px-3.5 py-2 text-sm bg-white border border-slate-300 rounded-xl text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-600/20 focus:border-emerald-600"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsCreateOpen(false)}
                  className="px-4 py-2 text-xs font-semibold rounded-xl text-slate-600 hover:bg-slate-100 transition"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || !newProjectName.trim()}
                  className="px-4 py-2 text-xs font-semibold rounded-xl text-white bg-slate-900 hover:bg-slate-800 disabled:opacity-50 transition"
                >
                  {isSubmitting ? "Đang tạo..." : "Tạo Dự Án"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
