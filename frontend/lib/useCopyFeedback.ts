"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Copy-button feedback state, shared by Dashboard and ChatStream.
 *
 * Both previously reimplemented the same "flash a Check for 2s than revert"
 * dance with a raw boolean + setTimeout. The timer is cleaned up on unmount so
 * a switched-away component can't flip state for a mounted sibling.
 */
export function useCopyFeedback() {
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () => () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    },
    []
  );

  const markCopied = useCallback((id: string | null = null) => {
    setCopiedId(id);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setCopiedId(null), 2000);
  }, []);

  return { copiedId, markCopied };
}