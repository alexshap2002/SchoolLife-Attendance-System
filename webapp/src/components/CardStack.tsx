import React, { useState, useCallback } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import SwipeCard from './SwipeCard'
import { Student, SwipeDirection, AttendanceStatus, AttendanceEvent } from '../types'
import { useTelegramStore } from '../stores/telegramStore'

interface CardStackProps {
  students: Student[];
  sessionId: number;
  onAttendanceChange: (events: AttendanceEvent[]) => void;
  onComplete: () => void;
}

const CardStack: React.FC<CardStackProps> = ({ 
  students, 
  sessionId, 
  onAttendanceChange,
  onComplete 
}) => {
  const { hapticFeedback, setMainButton, hideMainButton } = useTelegramStore()
  const [currentIndex, setCurrentIndex] = useState(0)
  const [attendanceEvents, setAttendanceEvents] = useState<AttendanceEvent[]>([])
  const [removedCards, setRemovedCards] = useState<Set<number>>(new Set())

  // Cards to show (current + next 2 for stack effect)
  const visibleCards = students.slice(currentIndex, currentIndex + 3)
  const isLastCard = currentIndex >= students.length - 1

  const handleSwipe = useCallback((direction: SwipeDirection, status?: AttendanceStatus) => {
    const currentStudent = students[currentIndex]
    if (!currentStudent) return

    let newEvent: AttendanceEvent | null = null

    // Only create attendance event for up/down swipes
    if (status && (direction === 'up' || direction === 'down')) {
      newEvent = {
        session_id: sessionId,
        student_id: currentStudent.id,
        status,
        timestamp: Date.now()
      }

      setAttendanceEvents(prev => {
        const updated = [...prev, newEvent!]
        onAttendanceChange(updated)
        return updated
      })
    }

    // Mark card as removed for animation
    setRemovedCards(prev => new Set([...prev, currentIndex]))

    // Move to next card after animation delay
    setTimeout(() => {
      const nextIndex = currentIndex + 1
      setCurrentIndex(nextIndex)
      
      // Check if we've reached the end
      if (nextIndex >= students.length) {
        onComplete()
        return
      }

      // Update main button text
      const remaining = students.length - nextIndex
      if (remaining > 0) {
        setMainButton(
          `📝 Завершити (${attendanceEvents.length + (newEvent ? 1 : 0)}/${students.length})`,
          onComplete
        )
      }
    }, 300)

    // Provide haptic feedback based on action
    if (direction === 'up') {
      hapticFeedback('success')
    } else if (direction === 'down') {
      hapticFeedback('error')
    } else {
      hapticFeedback('light')
    }
  }, [currentIndex, students, sessionId, attendanceEvents, onAttendanceChange, onComplete, hapticFeedback, setMainButton])

  // Update main button when component mounts/unmounts
  React.useEffect(() => {
    if (students.length > 0) {
      setMainButton(
        `📝 Завершити (${attendanceEvents.length}/${students.length})`,
        onComplete
      )
    }

    return () => {
      hideMainButton()
    }
  }, [students.length, attendanceEvents.length, onComplete, setMainButton, hideMainButton])

  if (students.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center">
          <div className="text-6xl mb-4">👥</div>
          <h3 className="text-xl font-semibold text-gray-700 dark:text-gray-300 mb-2">
            Немає студентів
          </h3>
          <p className="text-gray-500 dark:text-gray-400">
            У цій групі поки що немає доданих студентів
          </p>
        </div>
      </div>
    )
  }

  if (currentIndex >= students.length) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <motion.div
          className="text-center"
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: "spring", duration: 0.6 }}
        >
          <div className="text-6xl mb-4">🎉</div>
          <h3 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-2">
            Відмітка завершена!
          </h3>
          <p className="text-lg text-gray-600 dark:text-gray-300 mb-4">
            Відмічено {attendanceEvents.length} з {students.length} студентів
          </p>
          <div className="text-4xl">
            ✅ {attendanceEvents.filter(e => e.status === 'present').length} присутніх
            {' '}
            ❌ {attendanceEvents.filter(e => e.status === 'absent').length} відсутніх
          </div>
        </motion.div>
      </div>
    )
  }

  return (
    <div className="flex-1 relative card-stack">
      {/* Progress bar */}
      <div className="absolute top-4 left-4 right-4 z-20">
        <div className="bg-gray-200 dark:bg-gray-700 rounded-full h-2">
          <motion.div
            className="bg-telegram-link h-2 rounded-full"
            initial={{ width: 0 }}
            animate={{ width: `${(currentIndex / students.length) * 100}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>
        <div className="flex justify-between items-center mt-2 text-sm text-gray-600 dark:text-gray-300">
          <span>{currentIndex + 1} з {students.length}</span>
          <span>
            ✅ {attendanceEvents.filter(e => e.status === 'present').length}
            {' '}
            ❌ {attendanceEvents.filter(e => e.status === 'absent').length}
          </span>
        </div>
      </div>

      {/* Card stack */}
      <AnimatePresence>
        {visibleCards.map((student, index) => {
          const cardIndex = currentIndex + index
          const isTop = index === 0
          const isRemoved = removedCards.has(cardIndex)

          if (isRemoved) return null

          return (
            <SwipeCard
              key={`${student.id}-${cardIndex}`}
              student={student}
              onSwipe={handleSwipe}
              isTop={isTop}
              index={index}
            />
          )
        })}
      </AnimatePresence>

      {/* Instructions overlay (only for first card) */}
      {currentIndex === 0 && (
        <motion.div
          className="absolute bottom-20 left-4 right-4 z-20"
          initial={{ opacity: 1 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
        >
          <div className="bg-black bg-opacity-50 text-white p-4 rounded-2xl text-center">
            <div className="text-lg font-semibold mb-2">
              📱 Як користуватися
            </div>
            <div className="text-sm space-y-1">
              <div>👆 <strong>Свайп вгору</strong> - дитина присутня</div>
              <div>👇 <strong>Свайп вниз</strong> - дитина відсутня</div>
              <div>👈👉 <strong>Свайп вбік</strong> - пропустити</div>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  )
}

export default CardStack
