import { useState } from 'react'
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd'

const FIELD_GROUPS = [
  {
    group: 'Geography',
    color: 'blue',
    fields: [
      { id: 'state',    label: 'State',       icon: '🗺' },
      { id: 'district', label: 'District',    icon: '📍' },
      { id: 'sector',   label: 'Urban/Rural', icon: '🏘' },
    ]
  },
  {
    group: 'Demographics',
    color: 'purple',
    fields: [
      { id: 'gender',    label: 'Gender',    icon: '👤' },
      { id: 'age',       label: 'Age Group', icon: '📊' },
      { id: 'education', label: 'Education', icon: '🎓' },
    ]
  },
  {
    group: 'Time',
    color: 'green',
    fields: [
      { id: 'year',  label: 'Survey Year',  icon: '📅' },
      { id: 'round', label: 'Survey Round', icon: '🔄' },
    ]
  },
  {
    group: 'Indicators',
    color: 'orange',
    fields: [
      { id: 'employment_rate',    label: 'Employment Rate',    icon: '📈' },
      { id: 'unemployment_rate',  label: 'Unemployment Rate',  icon: '📉' },
      { id: 'lfpr',               label: 'LFPR',               icon: '⚡' },
      { id: 'income',             label: 'Income',             icon: '💰' },
      { id: 'consumption',        label: 'Consumption',        icon: '🛒' },
    ]
  },
  {
    group: 'Aggregation',
    color: 'slate',
    fields: [
      { id: 'count',      label: 'Count',      icon: '#' },
      { id: 'average',    label: 'Average',    icon: '~' },
      { id: 'percentage', label: 'Percentage', icon: '%' },
      { id: 'sum',        label: 'Sum',        icon: '∑' },
    ]
  },
  {
    group: 'Visualization',
    color: 'pink',
    fields: [
      { id: 'bar',       label: 'Bar Chart',    icon: '▊' },
      { id: 'pie',       label: 'Pie Chart',    icon: '◕' },
      { id: 'line',      label: 'Line Chart',   icon: '↗' },
      { id: 'table',     label: 'Table',        icon: '⊞' },
      { id: 'heatmap',   label: 'Heatmap',      icon: '🌡' },
    ]
  },
]

const COLOR_MAP = {
  blue:   { pill:'bg-blue-100 text-blue-800 border-blue-200',   head:'text-blue-600'   },
  purple: { pill:'bg-purple-100 text-purple-800 border-purple-200', head:'text-purple-600' },
  green:  { pill:'bg-green-100 text-green-800 border-green-200',  head:'text-green-600'  },
  orange: { pill:'bg-orange-100 text-orange-800 border-orange-200', head:'text-orange-600' },
  slate:  { pill:'bg-slate-100 text-slate-800 border-slate-200',  head:'text-slate-600'  },
  pink:   { pill:'bg-pink-100 text-pink-800 border-pink-200',    head:'text-pink-600'   },
}

const ZONE_CONFIG = [
  { id:'rows',    label:'Row Filters',   icon:'↕', hint:'Drag dimensions here' },
  { id:'columns', label:'Column Fields', icon:'↔', hint:'Drag measures here'   },
  { id:'filters', label:'Filters',       icon:'⊟', hint:'Drag filters here'    },
  { id:'viz',     label:'Visualization', icon:'◈', hint:'Drag chart type here' },
]

export default function QueryBuilder({ onQuery, isQuerying, filename }) {
  const [zones, setZones] = useState({ rows:[], columns:[], filters:[], viz:[] })
  const [usedIds, setUsedIds] = useState(new Set())

  const allFields = FIELD_GROUPS.flatMap(g =>
    g.fields.map(f => ({ ...f, group: g.group, color: g.color }))
  )

  const findField = (id) => allFields.find(f => f.id === id)

  const onDragEnd = (result) => {
    const { source, destination, draggableId } = result
    if (!destination) return

    // from panel to a zone
    if (source.droppableId === 'panel') {
      if (destination.droppableId === 'panel') return
      if (usedIds.has(draggableId)) return
      const field = findField(draggableId)
      if (!field) return
      setZones(z => ({
        ...z,
        [destination.droppableId]: [...z[destination.droppableId], field]
      }))
      setUsedIds(u => new Set([...u, draggableId]))
      return
    }

    // reorder within a zone
    if (source.droppableId === destination.droppableId) {
      const zone = [...zones[source.droppableId]]
      const [moved] = zone.splice(source.index, 1)
      zone.splice(destination.index, 0, moved)
      setZones(z => ({ ...z, [source.droppableId]: zone }))
      return
    }

    // move between zones
    const from = [...zones[source.droppableId]]
    const to   = [...zones[destination.droppableId]]
    const [moved] = from.splice(source.index, 1)
    to.splice(destination.index, 0, moved)
    setZones(z => ({ ...z, [source.droppableId]: from, [destination.droppableId]: to }))
  }

  const removeFromZone = (zoneId, fieldId) => {
    setZones(z => ({ ...z, [zoneId]: z[zoneId].filter(f => f.id !== fieldId) }))
    setUsedIds(u => { const n = new Set(u); n.delete(fieldId); return n })
  }

  const clearAll = () => {
    setZones({ rows:[], columns:[], filters:[], viz:[] })
    setUsedIds(new Set())
  }

  const hasFields = Object.values(zones).some(z => z.length > 0)

  const buildQueryLabel = () => {
    const rows = zones.rows.map(f => f.label).join(', ')   || '—'
    const cols = zones.columns.map(f => f.label).join(', ')|| '—'
    const fil  = zones.filters.map(f => f.label).join(', ')|| '—'
    const viz  = zones.viz[0]?.label || 'Table'
    return { rows, cols, fil, viz }
  }

  const q = buildQueryLabel()

  return (
    <DragDropContext onDragEnd={onDragEnd}>
      <div className="space-y-4">

        {/* Active dataset notice */}
        <div className="flex items-center gap-2 bg-amber-50 border border-amber-200 rounded-lg px-4 py-2.5">
          <span className="text-amber-500">🔒</span>
          <p className="text-amber-700 text-sm">
            Query will run only on <strong>{filename}</strong>
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

          {/* LEFT — Field Panel */}
          <div className="lg:col-span-1">
            <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
              <div className="gradient-dark px-4 py-3">
                <p className="text-white font-semibold text-sm">Field Panel</p>
                <p className="text-slate-400 text-xs mt-0.5">Drag fields into the canvas →</p>
              </div>

              <Droppable droppableId="panel" isDropDisabled={true}>
                {(provided) => (
                  <div
                    ref={provided.innerRef}
                    {...provided.droppableProps}
                    className="p-3 space-y-4 max-h-[520px] overflow-y-auto"
                  >
                    {FIELD_GROUPS.map((group) => {
                      const c = COLOR_MAP[group.color]
                      return (
                        <div key={group.group}>
                          <p className={`text-xs font-bold uppercase tracking-wider mb-2 ${c.head}`}>
                            {group.group}
                          </p>
                          <div className="space-y-1.5">
                            {group.fields.map((field, index) => {
                              const isUsed = usedIds.has(field.id)
                              return (
                                <Draggable
                                  key={field.id}
                                  draggableId={field.id}
                                  index={index}
                                  isDragDisabled={isUsed}
                                >
                                  {(prov, snap) => (
                                    <div
                                      ref={prov.innerRef}
                                      {...prov.draggableProps}
                                      {...prov.dragHandleProps}
                                      className={`flex items-center gap-2.5 px-3 py-2 rounded-lg border text-xs font-medium cursor-grab transition-all
                                        ${isUsed
                                          ? 'opacity-35 cursor-not-allowed bg-slate-50 border-slate-200 text-slate-400'
                                          : snap.isDragging
                                            ? `${c.pill} shadow-lg scale-105`
                                            : `${c.pill} hover:shadow-sm hover:scale-[1.02]`
                                        }`}
                                    >
                                      <span className="text-sm">{field.icon}</span>
                                      <span>{field.label}</span>
                                      {!isUsed && (
                                        <span className="ml-auto text-slate-300">⠿</span>
                                      )}
                                      {isUsed && (
                                        <span className="ml-auto text-slate-300 text-xs">✓</span>
                                      )}
                                    </div>
                                  )}
                                </Draggable>
                              )
                            })}
                          </div>
                        </div>
                      )
                    })}
                    {provided.placeholder}
                  </div>
                )}
              </Droppable>
            </div>
          </div>

          {/* RIGHT — Drop Canvas */}
          <div className="lg:col-span-2 space-y-4">

            {/* 4 drop zones */}
            <div className="grid grid-cols-2 gap-3">
              {ZONE_CONFIG.map(zone => (
                <Droppable key={zone.id} droppableId={zone.id}>
                  {(provided, snap) => (
                    <div
                      ref={provided.innerRef}
                      {...provided.droppableProps}
                      className={`min-h-[120px] rounded-xl border-2 border-dashed p-3 transition-all duration-200
                        ${snap.isDraggingOver
                          ? 'border-blue-400 bg-blue-50/80'
                          : 'border-slate-300 bg-slate-50/50'
                        }`}
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-slate-400 text-sm">{zone.icon}</span>
                        <p className="text-xs font-bold text-slate-600 uppercase tracking-wide">
                          {zone.label}
                        </p>
                      </div>

                      {zones[zone.id].length === 0 && (
                        <p className="text-xs text-slate-400 italic px-1">{zone.hint}</p>
                      )}

                      <div className="flex flex-wrap gap-1.5 mt-1">
                        {zones[zone.id].map((field, index) => {
                          const c = COLOR_MAP[field.color]
                          return (
                            <Draggable key={field.id} draggableId={`zone-${field.id}`} index={index}>
                              {(prov, snap) => (
                                <div
                                  ref={prov.innerRef}
                                  {...prov.draggableProps}
                                  {...prov.dragHandleProps}
                                  className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-semibold
                                    ${snap.isDragging ? 'shadow-lg' : ''} ${c.pill}`}
                                >
                                  <span>{field.icon}</span>
                                  <span>{field.label}</span>
                                  <button
                                    onClick={() => removeFromZone(zone.id, field.id)}
                                    className="ml-1 opacity-60 hover:opacity-100 text-xs leading-none"
                                  >
                                    ×
                                  </button>
                                </div>
                              )}
                            </Draggable>
                          )
                        })}
                      </div>
                      {provided.placeholder}
                    </div>
                  )}
                </Droppable>
              ))}
            </div>

            {/* Query preview */}
            {hasFields && (
              <div className="bg-slate-900 rounded-xl p-4 animate-fadeIn">
                <p className="text-slate-400 text-xs font-semibold uppercase tracking-wide mb-3">
                  Generated Query Preview
                </p>
                <div className="grid grid-cols-2 gap-2 text-xs mb-3">
                  {[
                    { label:'ROWS',    val: q.rows },
                    { label:'COLUMNS', val: q.cols },
                    { label:'FILTERS', val: q.fil  },
                    { label:'CHART',   val: q.viz  },
                  ].map(item => (
                    <div key={item.label} className="bg-slate-800 rounded-lg px-3 py-2">
                      <p className="text-slate-500 text-xs mb-0.5">{item.label}</p>
                      <p className="text-green-400 font-mono font-medium truncate">{item.val}</p>
                    </div>
                  ))}
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => onQuery(zones)}
                    disabled={isQuerying}
                    className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-semibold py-2.5 rounded-lg text-sm transition-colors animate-glow"
                  >
                    {isQuerying ? 'Running Query...' : '⚡ Run This Query'}
                  </button>
                  <button
                    onClick={clearAll}
                    className="px-4 py-2.5 border border-slate-600 text-slate-400 hover:text-white hover:border-slate-400 rounded-lg text-sm transition-colors"
                  >
                    Clear All
                  </button>
                </div>
              </div>
            )}

            {!hasFields && (
              <div className="bg-white border-2 border-dashed border-slate-200 rounded-xl p-8 text-center">
                <div className="text-4xl mb-3">⊞</div>
                <p className="text-slate-500 font-medium text-sm">Drag fields from the left panel</p>
                <p className="text-slate-400 text-xs mt-1">into the zones above to build your query</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </DragDropContext>
  )
}