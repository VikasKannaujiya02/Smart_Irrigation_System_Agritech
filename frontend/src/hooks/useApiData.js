import { useCallback, useEffect, useRef, useState } from 'react'

const useApiData = (fetcher, dependencies = [], options = {}) => {
  const { intervalMs = 0 } = options
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const fetcherRef = useRef(fetcher)

  useEffect(() => {
    fetcherRef.current = fetcher
  }, [fetcher])

  const load = useCallback(async () => {
    try {
      setError(null)
      const result = await fetcherRef.current()
      setData(result)
    } catch (err) {
      setError(err)
    } finally {
      setLoading(false)
    }
  }, dependencies)

  useEffect(() => {
    let active = true

    const run = async () => {
      try {
        setError(null)
        const result = await fetcherRef.current()
        if (active) {
          setData(result)
        }
      } catch (err) {
        if (active) {
          setError(err)
        }
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    setLoading(true)
    run()

    if (!intervalMs) {
      return () => {
        active = false
      }
    }

    const intervalId = setInterval(run, intervalMs)
    return () => {
      active = false
      clearInterval(intervalId)
    }
  }, [intervalMs, ...dependencies])

  return { data, loading, error, refetch: load }
}

export default useApiData
