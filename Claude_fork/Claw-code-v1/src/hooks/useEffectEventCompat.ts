import { useCallback, useRef } from 'react'

type AnyFn = (...args: any[]) => any

export function useEffectEventCompat<T extends AnyFn>(callback: T): T {
  const callbackRef = useRef(callback)
  callbackRef.current = callback

  return useCallback(((...args: Parameters<T>) => callbackRef.current(...args)) as T, [])
}
