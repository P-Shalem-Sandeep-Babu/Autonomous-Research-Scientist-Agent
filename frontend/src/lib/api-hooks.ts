"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";

// Auth Hooks
export const useLogin = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (formData: FormData) => api.login(formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["me"] });
    },
  });
};

export const useRegister = () => {
  return useMutation({
    mutationFn: (userData: any) => api.register(userData),
  });
};

export const useGetMe = () => {
  return useQuery({
    queryKey: ["me"],
    queryFn: () => api.getMe(),
    retry: 1,
  });
};

// Projects Hooks
export const useGetProjects = () => {
  return useQuery({
    queryKey: ["projects"],
    queryFn: () => api.getProjects(),
  });
};

export const useCreateProject = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (projectData: any) => api.createProject(projectData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });
};

export const useGetProject = (id: string | number) => {
  return useQuery({
    queryKey: ["project", id],
    queryFn: () => api.getProject(id),
  });
};

export const useDeleteProject = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string | number) => api.deleteProject(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });
};

export const useGetCodeFile = (projectId: string | number, fileId: string | number) => {
  return useQuery({
    queryKey: ["codeFile", projectId, fileId],
    queryFn: () => api.getCodeFile(projectId, fileId),
  });
};

export const useGetProjectGraph = (projectId: string | number) => {
  return useQuery({
    queryKey: ["projectGraph", projectId],
    queryFn: () => api.getProjectGraph(projectId),
  });
};

// Analytics Hooks
export const useGetAnalytics = () => {
  return useQuery({
    queryKey: ["analytics"],
    queryFn: () => api.getAnalytics(),
  });
};