import { useEffect, useMemo, useState } from 'react'
import { Map, MapControls, MapMarker, MarkerContent, MarkerPopup } from './components/mapcn'
import { CalendarDays, MapPin, Plus, Trash2 } from 'lucide-react'
import './App.css'

type Place = {
  id: number
  name: string
  city: string
  timePoint: string
  durationYears: number
  event: string
  longitude: number
  latitude: number
}

const emptyDraft = { name: '', city: '', timePoint: '', durationYears: 0, event: '' }

function getDraft(place: Place) {
  return {
    name: place.name,
    city: place.city,
    timePoint: place.timePoint,
    durationYears: place.durationYears,
    event: place.event,
  }
}

function DatePicker({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return (
    <div className="date-picker">
      <CalendarDays size={15} aria-hidden="true" />
      <input
        type="date"
        lang="zh-CN"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-label="选择年月日"
      />
    </div>
  )
}

function App() {
  const [places, setPlaces] = useState<Place[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [draft, setDraft] = useState(emptyDraft)
  const [dataStatus, setDataStatus] = useState<'loading' | 'saved' | 'saving' | 'error'>('loading')
  const selected = places.find((place) => place.id === selectedId) ?? null

  useEffect(() => {
    let cancelled = false
    fetch('/api/places')
      .then((response) => {
        if (!response.ok) throw new Error('读取本地节点失败')
        return response.json() as Promise<Place[]>
      })
      .then((data) => {
        if (cancelled) return
        setPlaces(data)
        setSelectedId(data[0]?.id ?? null)
        setDraft(data[0] ? getDraft(data[0]) : emptyDraft)
        setDataStatus('saved')
      })
      .catch(() => {
        if (!cancelled) setDataStatus('error')
      })
    return () => { cancelled = true }
  }, [])

  async function persistPlaces(nextPlaces: Place[]) {
    setDataStatus('saving')
    try {
      const response = await fetch('/api/places', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(nextPlaces),
      })
      if (!response.ok) throw new Error('保存本地节点失败')
      setDataStatus('saved')
    } catch {
      setDataStatus('error')
    }
  }
  const bounds = useMemo(() => {
    if (places.length === 0) return { center: [116.4, 35.9] as [number, number], zoom: 4.2 }
    const avg = places.reduce((acc, place) => [acc[0] + place.longitude, acc[1] + place.latitude], [0, 0])
    return { center: [avg[0] / places.length, avg[1] / places.length] as [number, number], zoom: places.length === 1 ? 6 : 4.3 }
  }, [places])

  async function addPlaceAt(lngLat: { lng: number; lat: number }) {
    const place = { id: Date.now(), name: '新地点', city: '', timePoint: new Date().toISOString().slice(0, 10), durationYears: 0, event: '', longitude: lngLat.lng, latitude: lngLat.lat }
    const nextPlaces = [...places, place]
    setPlaces(nextPlaces)
    setSelectedId(place.id)
    setDraft(getDraft(place))
    await persistPlaces(nextPlaces)
  }

  async function updateSelected() {
    if (!selected) return
    const nextPlaces = places.map((place) => place.id === selected.id ? { ...place, ...draft, name: draft.name || '未命名地点', durationYears: Number(draft.durationYears) || 0 } : place)
    setPlaces(nextPlaces)
    await persistPlaces(nextPlaces)
  }

  async function removeSelected() {
    if (!selected) return
    const nextPlaces = places.filter((place) => place.id !== selected.id)
    setPlaces(nextPlaces)
    setSelectedId(null)
    setDraft(emptyDraft)
    await persistPlaces(nextPlaces)
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand"><span className="brand-mark"><MapPin size={16} /></span><span>人生轨迹</span></div>
        <div className={`topbar-meta data-${dataStatus}`}><span className="live-dot" />{dataStatus === 'loading' ? '正在读取本地数据' : dataStatus === 'saving' ? '正在保存' : dataStatus === 'error' ? '本地数据保存失败' : '已保存到本地 JSON'} <span className="divider" /> 地图 + 标点</div>
      </header>
      <section className="workspace">
        <aside className="sidebar">
          <div className="sidebar-heading"><div><p className="eyebrow">LIFE MAP</p><h1>把经历放回地图上</h1></div><span className="count-badge">{places.length}</span></div>
          <p className="intro">先从地点开始，记录那些塑造过你的城市、住所和远方。</p>
          <div className="section-label"><span>已标记地点</span><span>{places.length} 个</span></div>
          <div className="place-list">
            {places.map((place) => <button key={place.id} className={`place-row ${selectedId === place.id ? 'selected' : ''}`} onClick={() => { setSelectedId(place.id); setDraft(getDraft(place)) }}><span className="row-pin"><MapPin size={15} /></span><span className="row-copy"><strong>{place.name}</strong><small>{place.city || '未填写城市'} · {place.event || '未填写事件'}</small></span><span className="row-arrow">›</span></button>)}
            {places.length === 0 && <div className="empty-state"><MapPin size={20} /><span>还没有地点<br />在地图上点击添加</span></div>}
          </div>
          <div className="editor">
            <div className="section-label"><span>当前标点</span><span className="coord">{selected ? `${selected.latitude.toFixed(2)}°, ${selected.longitude.toFixed(2)}°` : '未选择'}</span></div>
            {selected ? <><label>地点名称<input value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} /></label><label>城市<input value={draft.city} onChange={(event) => setDraft({ ...draft, city: event.target.value })} placeholder="例如：上海" /></label><div className="field-grid"><label>时间点<DatePicker value={draft.timePoint} onChange={(timePoint) => setDraft({ ...draft, timePoint })} /></label><label>持续时间（年）<input type="number" min="0" step="0.1" value={draft.durationYears} onChange={(event) => setDraft({ ...draft, durationYears: Number(event.target.value) })} /></label></div><label>事件<textarea value={draft.event} onChange={(event) => setDraft({ ...draft, event: event.target.value })} rows={3} placeholder="记录这段经历发生了什么" /></label><div className="editor-actions"><button className="save-button" onClick={updateSelected}>保存修改</button><button className="icon-button danger" onClick={removeSelected} aria-label="删除当前标点"><Trash2 size={16} /></button></div></> : <p className="editor-empty">选择一个地点，编辑它的五项信息。</p>}
          </div>
          <div className="hint"><Plus size={15} /><span>点击地图任意位置，快速添加人生节点</span></div>
        </aside>
        <div className="map-panel">
          <Map center={bounds.center} zoom={bounds.zoom} minZoom={2} maxZoom={18} className="map-canvas" onClick={(event) => addPlaceAt(event.lngLat)}>
            {places.map((place) => <MapMarker key={place.id} longitude={place.longitude} latitude={place.latitude} onClick={() => { setSelectedId(place.id); setDraft(getDraft(place)) }}><MarkerContent className={selectedId === place.id ? 'marker-selected' : ''}><span className="marker-pin"><MapPin size={18} fill="currentColor" /></span></MarkerContent>{selectedId === place.id && <MarkerPopup><strong>{place.name}</strong><span>{place.city || '未填写城市'} · {place.timePoint || '未填写时间点'}</span><span>{place.durationYears ? `${place.durationYears} 年` : '未填写持续时间'}</span><span>{place.event || '未填写事件'}</span></MarkerPopup>}</MapMarker>)}
            <MapControls />
          </Map>
          <div className="map-overlay"><span className="overlay-title">中国 · 人生节点</span><span className="overlay-subtitle">拖动地图探索 · 点击添加标点</span></div>
          <div className="map-legend"><span className="legend-dot" />已记录 <span className="legend-line" /> CARTO / OpenStreetMap</div>
        </div>
      </section>
    </main>
  )
}

export default App
