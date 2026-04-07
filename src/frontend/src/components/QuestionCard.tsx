import { useState } from 'react'
import { HelpCircle, Check } from 'lucide-react'
import { Card, CardContent } from './ui/card'
import { Button } from './ui/button'
import { Badge } from './ui/badge'

interface Question {
  question: string
  options: Array<{ label: string; description?: string }>
  multiSelect?: boolean
}

interface QuestionCardProps {
  questions: Question[]
  onSubmitAnswers: (answers: { [key: string]: string }) => void
}

export default function QuestionCard({ questions, onSubmitAnswers }: QuestionCardProps) {
  // Initialize with default answers (first option for single-select questions)
  const [answers, setAnswers] = useState<{ [key: string]: string }>(() => {
    const defaultAnswers: { [key: string]: string } = {}
    questions.forEach(q => {
      if (!q.multiSelect && q.options && q.options.length > 0) {
        // For single-select, default to first option
        const firstOption = q.options[0]
        defaultAnswers[q.question] = firstOption.label
      }
    })
    console.log('Initial default answers:', defaultAnswers)
    return defaultAnswers
  })
  const [isSubmitted, setIsSubmitted] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const handleAnswerChange = (questionText: string, answer: string, isMultiSelect: boolean) => {
    console.log('handleAnswerChange called:', { questionText, answer, isMultiSelect })

    if (isMultiSelect) {
      // Handle multi-select (checkboxes)
      const currentAnswers = answers[questionText]?.split(',').filter(Boolean) || []
      const updatedAnswers = currentAnswers.includes(answer)
        ? currentAnswers.filter(a => a !== answer)
        : [...currentAnswers, answer]

      const newAnswer = updatedAnswers.join(',')
      console.log('Setting multi-select answer:', newAnswer)

      setAnswers(prev => {
        const updated = {
          ...prev,
          [questionText]: newAnswer
        }
        console.log('Updated answers (multi):', updated)
        return updated
      })
    } else {
      // Handle single-select (radio)
      console.log('Setting single-select answer:', answer)

      setAnswers(prev => {
        const updated = {
          ...prev,
          [questionText]: answer
        }
        console.log('Updated answers (single):', updated)
        return updated
      })
    }
  }

  const handleSubmit = async () => {
    setIsLoading(true)
    try {
      await onSubmitAnswers(answers)
      setIsSubmitted(true)
    } catch (error) {
      console.error('Error submitting answers:', error)
    } finally {
      setIsLoading(false)
    }
  }

  // Check if all questions are answered
  const allAnswered = questions.every(q => {
    const answer = answers[q.question]
    console.log(`Question: "${q.question}" -> Answer: "${answer}" -> Valid: ${answer && answer.trim().length > 0}`)
    return answer && answer.trim().length > 0
  })

  // Debug logging
  console.log('Full questions structure:', questions)
  console.log('Current answers object:', answers)
  console.log('All answered result:', allAnswered)
  console.log('Answer keys:', Object.keys(answers))
  console.log('Question keys:', questions.map(q => q.question))

  if (isSubmitted) {
    return (
      <div className="flex justify-start mb-3">
        <Card className="max-w-[80%] border-primary/50 bg-primary/10 border-2">
          <CardContent className="p-3">
            <div className="flex items-center gap-2 text-primary text-sm font-medium mb-2">
              <Check size={14} />
              <Badge variant="outline" className="border-primary text-primary">
                ANSWERS SUBMITTED
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground">
              Thank you for providing the clarifications.
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="flex justify-start mb-3">
      <Card className="max-w-[80%] border-primary/50 bg-primary/10 border-2">
        <CardContent className="p-4">
          <div className="flex items-center gap-2 text-primary text-sm font-medium mb-4">
            <HelpCircle size={14} />
            <Badge variant="outline" className="border-primary text-primary">
              CLARIFYING QUESTIONS
            </Badge>
          </div>

          <div className="space-y-4">
            {questions.map((question, qIndex) => {
              const hasAnswer = answers[question.question] && answers[question.question].trim().length > 0
              console.log('Rendering question:', question)
              console.log('Question options:', question.options)

              return (
                <div key={qIndex} className="space-y-2">
                  <h4 className="text-sm font-medium text-foreground flex items-center gap-2">
                    Q{qIndex + 1}: {question.question}
                    {hasAnswer && <span className="text-primary text-xs">✓</span>}
                  </h4>
                  <div className="space-y-1 ml-4">
                    {question.options?.map((option, oIndex) => {
                      console.log('Rendering option:', option, 'Type:', typeof option)
                      const isMultiSelect = question.multiSelect === true
                      const optionValue = option.label
                      const currentAnswers = answers[question.question]?.split(',').filter(Boolean) || []
                      const isSelected = isMultiSelect
                        ? currentAnswers.includes(optionValue)
                        : answers[question.question] === optionValue

                      return (
                        <label
                          key={oIndex}
                          className="flex items-start gap-2 cursor-pointer text-xs text-muted-foreground hover:text-foreground"
                          onClick={() => {
                            console.log('Label clicked:', { question: question.question, option: optionValue })
                          }}
                        >
                          <input
                            type={isMultiSelect ? "checkbox" : "radio"}
                            name={`question_${qIndex}`}
                            value={optionValue}
                            checked={isSelected}
                            onChange={() => {
                              console.log('Input onChange triggered:', { question: question.question, option: optionValue })
                              handleAnswerChange(question.question, optionValue, isMultiSelect)
                            }}
                            onClick={(e) => {
                              console.log('Input clicked:', { question: question.question, option: optionValue })
                              e.stopPropagation()
                            }}
                            className="mt-0.5 accent-primary"
                          />
                          <div>
                            <div className="font-medium">{option.label}</div>
                            {option.description && (
                              <div className="text-muted-foreground/70">{option.description}</div>
                            )}
                          </div>
                        </label>
                      )
                    })}
                  </div>
                </div>
              )
            })}
          </div>

          <div className="mt-4 flex justify-center">
            <Button
              onClick={handleSubmit}
              disabled={!allAnswered || isLoading}
              className="bg-primary hover:bg-primary/80 text-primary-foreground"
            >
              {isLoading ? 'Submitting...' : 'SUBMIT ANSWERS'}
              {!allAnswered && (
                <span className="ml-1 text-xs">
                  ({questions.length - Object.keys(answers).filter(key => answers[key]?.trim()).length} remaining)
                </span>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}