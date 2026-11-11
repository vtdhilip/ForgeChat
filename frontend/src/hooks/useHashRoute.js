import { useState, useEffect, useCallback } from 'react';

const CLEAN_PATH_ROUTES = new Set([
  'landing', 'features', 'solutions', 'pricing', 'about', 'contact', 'login',
  'privacy-policy', 'terms', 'data-deletion',
]);

function parseRoute() {
  const rawHash = (window.location.hash || '').replace(/^#\/?/, '');
  if (rawHash) {
    return rawHash.split('/').filter(Boolean).map(seg => {
      try { return decodeURIComponent(seg); } catch { return seg; }
    });
  }
  const rawPath = (window.location.pathname || '/').replace(/^\/+|\/+$/g, '');
  if (!rawPath) return [];
  return rawPath.split('/').filter(Boolean).map(seg => {
    try { return decodeURIComponent(seg); } catch { return seg; }
  });
}

function buildTargetUrl(parts) {
  const clean = parts.filter(p => p != null && p !== '').map(String);
  const first = clean[0];

  if (!first || first === 'landing') {
    return '/';
  }
  if (CLEAN_PATH_ROUTES.has(first)) {
    return '/' + clean.map(p => encodeURIComponent(p)).join('/');
  }
  // SaaS dashboard / internal routes stay hash-based at root path
  return '/#/' + clean.map(p => encodeURIComponent(p)).join('/');
}

function withSearch(target) {
  const search = window.location.search || '';
  if (!search) return target;
  const hashIdx = target.indexOf('#');
  if (hashIdx === -1) return `${target}${search}`;
  return `${target.slice(0, hashIdx)}${search}${target.slice(hashIdx)}`;
}

export function useHashRoute() {
  const [parts, setParts] = useState(parseRoute);

  useEffect(() => {
    const onChange = () => setParts(parseRoute());
    window.addEventListener('hashchange', onChange);
    window.addEventListener('popstate', onChange);
    return () => {
      window.removeEventListener('hashchange', onChange);
      window.removeEventListener('popstate', onChange);
    };
  }, []);

  const navigate = useCallback((...newParts) => {
    const nextUrl = withSearch(buildTargetUrl(newParts));
    const currentUrl = window.location.pathname + window.location.search + window.location.hash;
    if (nextUrl !== currentUrl) {
      window.history.pushState(null, '', nextUrl);
      if (!newParts[0] || CLEAN_PATH_ROUTES.has(newParts[0])) {
        window.scrollTo?.({ top: 0, behavior: 'auto' });
      }
    }
    setParts(parseRoute());
  }, []);

  const replace = useCallback((...newParts) => {
    const nextUrl = withSearch(buildTargetUrl(newParts));
    const currentUrl = window.location.pathname + window.location.search + window.location.hash;
    if (nextUrl !== currentUrl) {
      window.history.replaceState(null, '', nextUrl);
    }
    setParts(parseRoute());
  }, []);

  return [parts, navigate, replace];
}
