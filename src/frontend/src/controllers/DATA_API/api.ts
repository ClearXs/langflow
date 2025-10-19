/**
 * DATA_API - Data Management System API Configuration (React Hook Version)
 */

import axios, {
  type AxiosError,
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosResponse,
} from "axios";
import { useCallback, useEffect, useRef } from "react";
import { useUrlParam } from "@/hooks/use-iframe-params";

export interface DataAPIConfig {
  baseURL: string;
  timeout?: number;
  clientId?: string;
  clientSecret?: string;
  tokenHeader?: string;
  enableEncryption?: boolean;
  enableProgress?: boolean;
  statusWhiteList?: number[];
}

export interface RequestMeta {
  isToken?: boolean;
  isSerialize?: boolean;
  cryptoToken?: boolean;
  cryptoData?: boolean;
  isFormData?: boolean;
  skipAuth?: boolean;
  showProgress?: boolean;
}

export interface DataRequestConfig extends AxiosRequestConfig {
  meta?: RequestMeta;
  authorization?: boolean;
  cryptoToken?: boolean;
  cryptoData?: boolean;
  isFormData?: boolean;
  text?: boolean;
  _retry?: boolean;
}

const DEFAULT_CONFIG: DataAPIConfig = {
  baseURL: "/data-api",
  timeout: 10000,
  clientId: "saber3",
  clientSecret: "saber3_secret",
  tokenHeader: "Blade-Auth",
  enableEncryption: false,
  enableProgress: true,
  statusWhiteList: [],
};

// ============================================================================
// Utilities
// ============================================================================

function validatenull(val: any): boolean {
  return val === null || val === undefined || val === "";
}

function serialize(data: Record<string, any>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(data)) {
    params.append(key, String(value));
  }
  return params.toString();
}

// ============================================================================
// Error & Token Refresh Handlers (可被覆盖)
// ============================================================================

export let showError = (message: string): void => {
  console.error("[DATA_API]", message);
};

export let refreshAccessToken = async (): Promise<void> => {};

// ============================================================================
// React Hook: useDataAPI
// ============================================================================

export interface UseDataAPIOptions {
  config?: Partial<DataAPIConfig>;
  onError?: (message: string) => void;
  onRefreshToken?: () => Promise<void>;
  onLogout?: () => void;
}

/**
 * useDataAPI - React Hook for managing API instance with interceptors
 *
 * @example
 * ```tsx
 * const api = useDataAPI({
 *   config: { baseURL: "/api" },
 *   onError: (msg) => toast.error(msg),
 *   onRefreshToken: async () => { ... },
 *   onLogout: () => router.push("/login")
 * });
 * ```
 */
export function useDataAPI(options: UseDataAPIOptions = {}): AxiosInstance {
  const { config = {}, onError, onRefreshToken, onLogout } = options;

  const apiRef = useRef<AxiosInstance | null>(null);
  const isErrorShownRef = useRef(false);
  const configRef = useRef<DataAPIConfig>({ ...DEFAULT_CONFIG, ...config });

  const token = useUrlParam("token");

  if (!apiRef.current) {
    apiRef.current = axios.create({
      baseURL: configRef.current.baseURL,
      timeout: configRef.current.timeout,
      validateStatus: (status) => status >= 200 && status <= 500,
      withCredentials: true,
    });
  }

  const api = apiRef.current;

  // 覆盖全局错误处理函数
  useEffect(() => {
    if (onError) {
      showError = onError;
    }
  }, [onError]);

  // 覆盖全局 token 刷新函数
  useEffect(() => {
    if (onRefreshToken) {
      refreshAccessToken = onRefreshToken;
    }
  }, [onRefreshToken]);

  const handleUnauthorized = useCallback(
    async (
      config: DataRequestConfig,
      response: AxiosResponse,
    ): Promise<AxiosResponse> => {
      return Promise.reject();
    },
    [api],
  );

  // 设置请求拦截器
  useEffect(() => {
    const requestInterceptor = api.interceptors.request.use(
      (config: DataRequestConfig) => {
        const isMinioFile = config.url && config.url.startsWith("/minio-file");
        if (isMinioFile) {
          return config;
        }

        // Add security headers
        if (!config.headers) {
          config.headers = {} as any;
        }
        config.headers["Blade-Requested-With"] = "BladeHttpRequest";

        config.headers["Authorization"] = "Basic c2FiZXIzOnNhYmVyM19zZWNyZXQ=";
        config.headers[DEFAULT_CONFIG.tokenHeader] =
          token ||
          "bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJibGFkZXguY24iLCJhdWQiOlsiYmxhZGV4Il0sInRva2VuX3R5cGUiOiJhY2Nlc3NfdG9rZW4iLCJjbGllbnRfaWQiOiJzYWJlcjMiLCJ0ZW5hbnRfaWQiOiIwMDAwMDAiLCJ1c2VyX2lkIjoiMTEyMzU5ODgyMTczODY3NTIwMSIsImRlcHRfaWQiOiIxMTIzNTk4ODEzNzM4Njc1MjAxIiwicG9zdF9pZCI6IjExMjM1OTg4MTc3Mzg2NzUyMDEiLCJyb2xlX2lkIjoiMTEyMzU5ODgxNjczODY3NTIwMSwxOTEyMzk2MDkzMzk1MTQ0NzA2Iiwib2F1dGhfaWQiOiIiLCJhY2NvdW50IjoiYWRtaW4iLCJ1c2VyX25hbWUiOiJhZG1pbiIsIm5pY2tfbmFtZSI6IueuoeeQhuWRmCIsInJlYWxfbmFtZSI6IueuoeeQhuWRmCIsInJvbGVfbmFtZSI6ImFkbWluaXN0cmF0b3Is5pWw5o2u566h55CG5Yaz562W6ICFIiwiZGV0YWlsIjp7InR5cGUiOiJ3ZWIiLCJleHQiOiI0NueUqOaIt-W5s-WPsOafpeivoue7k-aenCJ9LCJleHAiOjE3NjQwMjM4MzIsIm5iZiI6MTc2MDQyMzgzMn0.I9sKs0DKTiB9gLO21AOOEsiQ2ofDMGQVowxgdI8_JZk";

        // Get metadata
        const meta = config.meta || {};
        // Add access token
        if (config.text === true) {
          config.headers["Content-Type"] = "text/plain";
        }
        if (config.isFormData || meta.isFormData) {
          config.headers["Content-Type"] = "multipart/form-data";
        }

        // Serialize form data
        if (config.method === "post" && meta.isSerialize === true) {
          config.data = serialize(config.data);
        }

        return config;
      },
      (error) => {
        return Promise.reject(error);
      },
    );

    return () => {
      api.interceptors.request.eject(requestInterceptor);
    };
  }, [api]);

  // 设置响应拦截器
  useEffect(() => {
    const responseInterceptor = api.interceptors.response.use(
      (res: AxiosResponse) => {
        const config = res.config as DataRequestConfig;
        // Get status and message
        const status = res.data.error_code || res.data.code || res.status;
        const statusWhiteList = configRef.current.statusWhiteList || [];
        const message =
          res.data.msg || res.data.error_description || "System error";

        // Handle whitelisted status codes
        if (statusWhiteList.includes(status)) {
          return Promise.reject(res);
        }

        // Handle 401 unauthorized
        if (status === 401 && !config._retry) {
          return handleUnauthorized(config, res);
        }

        // Handle 401 after retry
        if (status === 401 && config._retry) {
          handleAuthenticationError(message);
          return Promise.reject(new Error(message));
        }

        // Handle OAuth2 errors
        if (status > 2000 && !validatenull(res.data.error_description)) {
          if (!isErrorShownRef.current) {
            isErrorShownRef.current = true;
            showError(message);
          }
          return Promise.reject(new Error(message));
        }

        // Handle non-200 status
        if (status !== 200) {
          showError(message);
          return Promise.reject(new Error(message));
        }

        return res;
      },
      (error: AxiosError) => {
        return Promise.reject(error);
      },
    );

    return () => {
      api.interceptors.response.eject(responseInterceptor);
    };
  }, [api, handleUnauthorized]);

  return api;
}

function handleAuthenticationError(message: string): void {
  showError(message || "User token is unavailable, please login again");
}

export function createDataAPI(
  config: Partial<DataAPIConfig> = {},
): AxiosInstance {
  const finalConfig = { ...DEFAULT_CONFIG, ...config };
  const instance = axios.create({
    baseURL: finalConfig.baseURL,
    timeout: finalConfig.timeout,
    validateStatus: (status) => status >= 200 && status <= 500,
    withCredentials: true,
  });

  return instance;
}

export const dataAPI = createDataAPI();

export default useDataAPI;
