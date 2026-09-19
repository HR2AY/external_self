import React, { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { LocateFixed, Maximize, Minus, Plus, X } from 'lucide-react'
import * as maplibregl from 'maplibre-gl'
import type { Map as MapInstance, MarkerOptions, PopupOptions } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'

const lightStyle: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: 'raster',
      tiles: ['https://tile.openstreetmap.de/{z}/{x}/{y}.png'],
      tileSize: 256,
      attribution: '© OpenStreetMap contributors',
    },
  },
  layers: [{ id: 'osm', type: 'raster', source: 'osm', minzoom: 0, maxzoom: 19 }],
}

if (typeof window !== 'undefined' && !maplibregl.getWorkerUrl()) {
  maplibregl.setWorkerUrl(`https://unpkg.com/maplibre-gl@${maplibregl.getVersion()}/dist/maplibre-gl-worker.mjs`)
}

type MapContextValue = { map: MapInstance | null; loaded: boolean }
const MapContext = React.createContext<MapContextValue | null>(null)

export type MapProps = Omit<maplibregl.MapOptions, 'container' | 'style'> & {
  children?: ReactNode
  className?: string
  theme?: 'light' | 'dark'
  styles?: { light?: string | maplibregl.StyleSpecification; dark?: string | maplibregl.StyleSpecification }
  onClick?: (event: maplibregl.MapMouseEvent) => void
}

export function Map({ children, className, theme = 'light', styles, onClick, ...options }: MapProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [map, setMap] = useState<MapInstance | null>(null)
  const [loaded, setLoaded] = useState(false)
  const onClickRef = useRef(onClick)
  onClickRef.current = onClick
  const style = theme === 'dark'
    ? styles?.dark ?? lightStyle
    : styles?.light ?? lightStyle

  useEffect(() => {
    if (!containerRef.current) return
    const instance = new maplibregl.Map({
      container: containerRef.current,
      style,
      renderWorldCopies: false,
      attributionControl: { compact: true },
      ...options,
    })
    const onLoad = () => setLoaded(true)
    instance.on('load', onLoad)
    const handleClick = (event: maplibregl.MapMouseEvent) => onClickRef.current?.(event)
    instance.on('click', handleClick)
    setMap(instance)
    return () => {
      instance.off('load', onLoad)
      instance.off('click', handleClick)
      instance.remove()
      setMap(null)
      setLoaded(false)
    }
    // Map is intentionally initialized once, like mapcn's base component.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <MapContext.Provider value={{ map, loaded }}>
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} className={`relative h-full w-full ${className ?? ''}`}>
        {map && loaded && children}
      </div>
    </MapContext.Provider>
  )
}

function useMapContext() {
  const context = React.useContext(MapContext)
  if (!context) throw new Error('Map children must be rendered inside Map')
  return context
}

type MapMarkerProps = MarkerOptions & {
  longitude: number
  latitude: number
  children?: ReactNode
  onClick?: () => void
}

export function MapMarker({ longitude, latitude, children, onClick, ...options }: MapMarkerProps) {
  const { map } = useMapContext()
  const marker = useMemo(() => new maplibregl.Marker({ ...options, element: document.createElement('div') }).setLngLat([longitude, latitude]), [])

  useEffect(() => {
    if (!map) return
    marker.setLngLat([longitude, latitude]).addTo(map)
    const element = marker.getElement()
    if (onClick) element.addEventListener('click', onClick)
    return () => {
      if (onClick) element.removeEventListener('click', onClick)
      marker.remove()
    }
  }, [map, marker, longitude, latitude, onClick])

  return <MarkerContext.Provider value={marker}>{children}</MarkerContext.Provider>
}

const MarkerContext = React.createContext<maplibregl.Marker | null>(null)

export function MarkerContent({ children, className = '' }: { children?: ReactNode; className?: string }) {
  const marker = React.useContext(MarkerContext)
  if (!marker) return null
  return createPortal(
    <div className={`relative cursor-pointer ${className}`}>{children ?? <span className="marker-dot" />}</div>,
    marker.getElement(),
  )
}

export function MarkerPopup({ children, closeButton = true, ...options }: PopupOptions & { children: ReactNode; closeButton?: boolean }) {
  const marker = React.useContext(MarkerContext)
  const { map } = useMapContext()
  const container = useMemo(() => document.createElement('div'), [])
  const popup = useMemo(() => new maplibregl.Popup({ offset: 18, closeButton: false, ...options }).setDOMContent(container), [])

  useEffect(() => {
    if (!marker || !map) return
    marker.setPopup(popup)
    return () => {
      marker.setPopup(null)
    }
  }, [marker, map, popup])

  return createPortal(
    <div className="popup-card">
      {closeButton && <button className="popup-close" onClick={() => popup.remove()} aria-label="关闭标点详情"><X size={14} /></button>}
      {children}
    </div>,
    container,
  )
}

export function MapControls({ showLocate = true }: { showLocate?: boolean }) {
  const { map, loaded } = useMapContext()
  const [locating, setLocating] = useState(false)
  if (!map || !loaded) return null
  const mapInstance = map

  function locateCurrentPosition() {
    if (!navigator.geolocation) {
      window.alert('当前浏览器不支持定位功能')
      return
    }

    setLocating(true)
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        mapInstance.flyTo({
          center: [coords.longitude, coords.latitude],
          zoom: Math.max(mapInstance.getZoom(), 13),
          essential: true,
          duration: 1200,
        })
        setLocating(false)
      },
      (error) => {
        const message = error.code === error.PERMISSION_DENIED
          ? '请允许浏览器访问位置后再试'
          : '暂时无法获取当前位置，请稍后再试'
        window.alert(message)
        setLocating(false)
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 30000 },
    )
  }

  return (
    <div className="map-controls">
      <button onClick={() => map.zoomIn()} aria-label="放大"><Plus size={16} /></button>
      <button onClick={() => map.zoomOut()} aria-label="缩小"><Minus size={16} /></button>
      {showLocate && <button onClick={locateCurrentPosition} aria-label="定位当前位置" disabled={locating} title={locating ? '正在定位' : '定位当前位置'}><LocateFixed size={16} className={locating ? 'locating-icon' : ''} /></button>}
      <button onClick={() => map.getContainer().requestFullscreen?.()} aria-label="全屏"><Maximize size={16} /></button>
    </div>
  )
}
