import { HistoricalFinancials } from '@/types'
import { formatCurrency } from '@/lib/utils'

interface IncomeStatementProps {
  data: HistoricalFinancials[]
}

export function IncomeStatement({ data }: IncomeStatementProps) {
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
              Revenue
            </td>
            {data.map((year) => (
              <td key={year.year} className="px-3 py-2 whitespace-nowrap text-sm text-right text-gray-900">
                {year.revenue === 0 ? '-' : formatCurrency(year.revenue)}
              </td>
            ))}
          </tr>
          <tr className="bg-gray-50">
            <td className="px-3 py-2 whitespace-nowrap text-sm font-medium text-gray-900">
              Net Income
            </td>
            {data.map((year) => (
              <td key={year.year} className="px-3 py-2 whitespace-nowrap text-sm text-right text-gray-900">
                {year.net_income === 0 ? '-' : formatCurrency(year.net_income)}
              </td>
            ))}
          </tr>
          <tr>
            <td className="px-3 py-2 whitespace-nowrap text-sm font-medium text-gray-900">
              Net Margin
            </td>
            {data.map((year) => (
              <td key={year.year} className="px-3 py-2 whitespace-nowrap text-sm text-right text-gray-900">
                {year.revenue === 0 ? '-' : `${((year.net_income / year.revenue) * 100).toFixed(1)}%`}
              </td>
            ))}
          </tr>
          <tr className="bg-gray-50">
            <td className="px-3 py-2 whitespace-nowrap text-sm font-medium text-gray-900">
              Shares Outstanding
            </td>
            {data.map((year) => (
              <td key={year.year} className="px-3 py-2 whitespace-nowrap text-sm text-right text-gray-900">
                {year.shares_outstanding === 0 ? '-' : `${(year.shares_outstanding / 1e9).toFixed(2)}B`}
              </td>
            ))}
          </tr>
          <tr>
            <td className="px-3 py-2 whitespace-nowrap text-sm font-medium text-gray-900">
              Earnings Per Share
            </td>
            {data.map((year) => (
              <td key={year.year} className="px-3 py-2 whitespace-nowrap text-sm text-right text-gray-900">
                {year.shares_outstanding === 0 ? '-' : `$${(year.net_income / year.shares_outstanding).toFixed(2)}`}
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  )
}