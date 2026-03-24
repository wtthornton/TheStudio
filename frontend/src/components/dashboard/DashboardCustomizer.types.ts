export interface DashboardWidget {
  id: string
  label: string
  visible: boolean
  order: number
}

export interface DashboardView {
  name: string
  widgets: DashboardWidget[]
  isDefault?: boolean
}
