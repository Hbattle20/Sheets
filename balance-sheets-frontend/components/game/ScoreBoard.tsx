import { useGameStore } from '@/stores/gameStore'
import { Card, CardContent } from '@/components/ui/Card'

export default function ScoreBoard() {
  const { score, matches, totalGuesses, streak } = useGameStore()
  
  const accuracy = totalGuesses > 0 ? (matches / totalGuesses * 100).toFixed(1) : '0.0'

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
      <Card>
        <CardContent className="p-4 text-center">
          <p className="text-sm text-gray-600">Score</p>
          <p className="text-2xl font-bold">{score}</p>
        </CardContent>
      </Card>
      
      <Card>
        <CardContent className="p-4 text-center">
          <p className="text-sm text-gray-600">Matches</p>
          <p className="text-2xl font-bold">{matches}/{totalGuesses}</p>
        </CardContent>
      </Card>
      
      <Card>
        <CardContent className="p-4 text-center">
          <p className="text-sm text-gray-600">Accuracy</p>
          <p className="text-2xl font-bold">{accuracy}%</p>
        </CardContent>
      </Card>
      
      <Card>
        <CardContent className="p-4 text-center">
          <p className="text-sm text-gray-600">Streak</p>
          <p className="text-2xl font-bold">{streak}</p>
        </CardContent>
      </Card>
    </div>
  )
}