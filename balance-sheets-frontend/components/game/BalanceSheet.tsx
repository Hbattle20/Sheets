import { HistoricalFinancials } from '@/types'
import { formatCurrency } from '@/lib/utils'

interface BalanceSheetProps {
  data: HistoricalFinancials[]
}

export function BalanceSheet({ data }: BalanceSheetProps) {
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
              Total Assets
            </td>
            {data.map((year) => (
              <td key={year.year} className="px-3 py-2 whitespace-nowrap text-sm text-right text-gray-900">
                {year.assets === 0 ? '-' : formatCurrency(year.assets)}
              </td>
            ))}
          </tr>
          <tr className="bg-gray-50">
            <td className="px-3 py-2 whitespace-nowrap text-sm font-medium text-gray-900">
              Total Liabilities
            </td>
            {data.map((year) => (
              <td key={year.year} className="px-3 py-2 whitespace-nowrap text-sm text-right text-gray-900">
                {year.liabilities === 0 ? '-' : formatCurrency(year.liabilities)}
              </td>
            ))}
          </tr>
          <tr>
            <td className="px-3 py-2 whitespace-nowrap text-sm font-medium text-gray-900">
              Shareholders' Equity
            </td>
            {data.map((year) => (
              <td key={year.year} className="px-3 py-2 whitespace-nowrap text-sm text-right text-gray-900">
                {year.equity === 0 ? '-' : formatCurrency(year.equity)}
              </td>
            ))}
          </tr>
          <tr className="bg-gray-50">
            <td className="px-3 py-2 whitespace-nowrap text-sm font-medium text-gray-900">
              Cash & Equivalents
            </td>
            {data.map((year) => (
              <td key={year.year} className="px-3 py-2 whitespace-nowrap text-sm text-right text-gray-900">
                {year.cash === 0 ? '-' : formatCurrency(year.cash)}
              </td>
            ))}
          </tr>
          <tr>
            <td className="px-3 py-2 whitespace-nowrap text-sm font-medium text-gray-900">
              Total Debt
            </td>
            {data.map((year) => (
              <td key={year.year} className="px-3 py-2 whitespace-nowrap text-sm text-right text-gray-900">
                {year.debt === 0 ? '-' : formatCurrency(year.debt)}
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  )
}