import { HistoricalFinancials } from '@/types'
import { formatCurrency } from '@/lib/utils'

interface CashFlowStatementProps {
  data: HistoricalFinancials[]
}

export function CashFlowStatement({ data }: CashFlowStatementProps) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Item
            </th>
            {data.map((year) => (
              <th key={year.year} className="px-3 py-2 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                {year.year}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          <tr>
            <td className="px-3 py-2 whitespace-nowrap text-sm font-medium text-gray-900">
              Operating Cash Flow
            </td>
            {data.map((year) => (
              <td key={year.year} className="px-3 py-2 whitespace-nowrap text-sm text-right text-gray-900">
                {year.operating_cash_flow === 0 ? '-' : formatCurrency(year.operating_cash_flow)}
              </td>
            ))}
          </tr>
          <tr className="bg-gray-50">
            <td className="px-3 py-2 whitespace-nowrap text-sm font-medium text-gray-900">
              Free Cash Flow
            </td>
            {data.map((year) => (
              <td key={year.year} className="px-3 py-2 whitespace-nowrap text-sm text-right text-gray-900">
                {year.free_cash_flow === 0 ? '-' : formatCurrency(year.free_cash_flow)}
              </td>
            ))}
          </tr>
          <tr>
            <td className="px-3 py-2 whitespace-nowrap text-sm font-medium text-gray-900">
              FCF Margin
            </td>
            {data.map((year) => (
              <td key={year.year} className="px-3 py-2 whitespace-nowrap text-sm text-right text-gray-900">
                {year.revenue === 0 ? '-' : `${((year.free_cash_flow / year.revenue) * 100).toFixed(1)}%`}
              </td>
            ))}
          </tr>
          <tr className="bg-gray-50">
            <td className="px-3 py-2 whitespace-nowrap text-sm font-medium text-gray-900">
              FCF Per Share
            </td>
            {data.map((year) => (
              <td key={year.year} className="px-3 py-2 whitespace-nowrap text-sm text-right text-gray-900">
                {year.shares_outstanding === 0 ? '-' : `$${(year.free_cash_flow / year.shares_outstanding).toFixed(2)}`}
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  )
}