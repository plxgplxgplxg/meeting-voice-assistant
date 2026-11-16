"use client";

import React, { useState } from "react";
import { User, Lock, CheckCircle2, AlertCircle, Shield } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { fetchApi } from "@/lib/api";

export default function ProfilePage() {
  const { user, refreshUser } = useAuth();
  const [fullName, setFullName] = useState(user?.full_name || "");
  const [profileMsg, setProfileMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [isUpdatingProfile, setIsUpdatingProfile] = useState(false);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [passwordMsg, setPasswordMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [isUpdatingPassword, setIsUpdatingPassword] = useState(false);

  React.useEffect(() => {
    if (user?.full_name) {
      setFullName(user.full_name);
    }
  }, [user]);

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setProfileMsg(null);
    setIsUpdatingProfile(true);

    try {
      await fetchApi("/users/me", {
        method: "PUT",
        body: JSON.stringify({ full_name: fullName }),
      });
      await refreshUser();
      setProfileMsg({ type: "success", text: "Cập nhật hồ sơ thành công." });
    } catch (err: any) {
      setProfileMsg({ type: "error", text: err.message || "Không thể cập nhật hồ sơ." });
    } finally {
      setIsUpdatingProfile(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordMsg(null);
    setIsUpdatingPassword(true);

    try {
      await fetchApi("/users/me/password", {
        method: "PUT",
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });
      setPasswordMsg({ type: "success", text: "Đổi mật khẩu thành công." });
      setCurrentPassword("");
      setNewPassword("");
    } catch (err: any) {
      setPasswordMsg({ type: "error", text: err.message || "Mật khẩu hiện tại không chính xác." });
    } finally {
      setIsUpdatingPassword(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      <div className="pb-4 border-b border-slate-200">
        <h1 className="text-2xl font-bold text-slate-900">Cài Đặt Hồ Sơ</h1>
        <p className="text-sm font-medium text-slate-500 mt-1">
          Quản lý thông tin tài khoản và bảo mật
        </p>
      </div>

      {/* Profile Information */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
        <div className="flex items-center gap-3 pb-5 border-b border-slate-100">
          <div className="p-2.5 rounded-xl bg-slate-100 text-slate-800">
            <User className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900">Thông Tin Cá Nhân</h2>
            <p className="text-xs text-slate-500">Email và họ tên định danh tài khoản</p>
          </div>
        </div>

        {profileMsg && (
          <div
            className={`mt-4 p-3 rounded-xl flex items-center gap-2.5 text-xs font-semibold ${
              profileMsg.type === "success"
                ? "bg-emerald-50 border border-emerald-200 text-emerald-800"
                : "bg-rose-50 border border-rose-200 text-rose-800"
            }`}
          >
            {profileMsg.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            )}
            <span>{profileMsg.text}</span>
          </div>
        )}

        <form onSubmit={handleUpdateProfile} className="mt-5 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Địa Chỉ Email
            </label>
            <input
              type="email"
              disabled
              value={user?.email || ""}
              className="w-full px-3.5 py-2.5 text-sm bg-slate-50 border border-slate-200 rounded-xl text-slate-500 cursor-not-allowed"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Họ Và Tên
            </label>
            <input
              type="text"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full px-3.5 py-2.5 text-sm bg-white border border-slate-300 rounded-xl text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-600/20 focus:border-emerald-600 transition"
            />
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={isUpdatingProfile}
              className="px-5 py-2 text-sm font-semibold rounded-xl text-white bg-slate-900 hover:bg-slate-800 disabled:opacity-50 transition"
            >
              {isUpdatingProfile ? "Đang lưu..." : "Lưu Thay Đổi"}
            </button>
          </div>
        </form>
      </div>

      {/* Password Change */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
        <div className="flex items-center gap-3 pb-5 border-b border-slate-100">
          <div className="p-2.5 rounded-xl bg-slate-100 text-slate-800">
            <Lock className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900">Đổi Mật Khẩu</h2>
            <p className="text-xs text-slate-500">Bảo vệ tài khoản bằng mật khẩu an toàn</p>
          </div>
        </div>

        {passwordMsg && (
          <div
            className={`mt-4 p-3 rounded-xl flex items-center gap-2.5 text-xs font-semibold ${
              passwordMsg.type === "success"
                ? "bg-emerald-50 border border-emerald-200 text-emerald-800"
                : "bg-rose-50 border border-rose-200 text-rose-800"
            }`}
          >
            {passwordMsg.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            )}
            <span>{passwordMsg.text}</span>
          </div>
        )}

        <form onSubmit={handleChangePassword} className="mt-5 space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Mật Khẩu Hiện Tại
            </label>
            <input
              type="password"
              required
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full px-3.5 py-2.5 text-sm bg-white border border-slate-300 rounded-xl text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-600/20 focus:border-emerald-600 transition"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1.5">
              Mật Khẩu Mới (Tối thiểu 6 ký tự)
            </label>
            <input
              type="password"
              required
              minLength={6}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full px-3.5 py-2.5 text-sm bg-white border border-slate-300 rounded-xl text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-600/20 focus:border-emerald-600 transition"
            />
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={isUpdatingPassword}
              className="px-5 py-2 text-sm font-semibold rounded-xl text-white bg-slate-900 hover:bg-slate-800 disabled:opacity-50 transition"
            >
              {isUpdatingPassword ? "Đang cập nhật..." : "Cập Nhật Mật Khẩu"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
