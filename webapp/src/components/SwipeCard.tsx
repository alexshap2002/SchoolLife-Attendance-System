import React, { useState, useRef } from 'react'
import { motion, useMotionValue, useTransform, PanInfo } from 'framer-motion'
import { Student, SwipeDirection, AttendanceStatus } from '../types'
import { useTelegramStore } from '../stores/telegramStore'

interface SwipeCardProps {
  student: Student;
  onSwipe: (direction: SwipeDirection, status?: AttendanceStatus) => void;
  isTop: boolean;
  index: number;
}

const SwipeCard: React.FC<SwipeCardProps> = ({ student, onSwipe, isTop, index }) => {
  const { hapticFeedback } = useTelegramStore()
  const [isDragging, setIsDragging] = useState(false)
  const cardRef = useRef<HTMLDivElement>(null)
  
  const x = useMotionValue(0)
  const y = useMotionValue(0)
  const rotate = useTransform(x, [-200, 200], [-30, 30])
  const opacity = useTransform(x, [-200, -100, 0, 100, 200], [0, 1, 1, 1, 0])

  // Swipe indicators
  const presentOpacity = useTransform(y, [-100, -50, 0], [1, 0.5, 0])
  const absentOpacity = useTransform(y, [0, 50, 100], [0, 0.5, 1])

  const handleDragStart = () => {
    setIsDragging(true)
    hapticFeedback('light')
  }

  const handleDragEnd = (event: any, info: PanInfo) => {
    setIsDragging(false)
    
    const threshold = 100
    const { offset, velocity } = info
    
    // Determine swipe direction based on offset and velocity
    if (Math.abs(offset.y) > Math.abs(offset.x)) {
      // Vertical swipe
      if (offset.y < -threshold || velocity.y < -500) {
        // Swipe up - Present
        hapticFeedback('success')
        onSwipe('up', 'present')
      } else if (offset.y > threshold || velocity.y > 500) {
        // Swipe down - Absent  
        hapticFeedback('error')
        onSwipe('down', 'absent')
      }
    } else {
      // Horizontal swipe - Skip without marking
      if (Math.abs(offset.x) > threshold || Math.abs(velocity.x) > 500) {
        hapticFeedback('medium')
        onSwipe(offset.x > 0 ? 'right' : 'left')
      }
    }
    
    // Reset position if no swipe occurred
    x.set(0)
    y.set(0)
  }

  const getGenderEmoji = (gender?: 'male' | 'female') => {
    if (!gender) return '👤' // Default neutral avatar
    return gender === 'male' ? '👦' : '👧'
  }

  const getAgeGroup = (age: number) => {
    if (age <= 6) return 'малюк'
    if (age <= 10) return 'дитина'
    if (age <= 14) return 'підліток'
    return 'юнак'
  }

  return (
    <motion.div
      ref={cardRef}
      className={`absolute inset-4 swipe-card ${isTop ? 'z-10' : 'z-0'}`}
      style={{
        x,
        y,
        rotate,
        opacity: isTop ? opacity : 1,
        scale: isTop ? 1 : 0.95 - index * 0.02,
        zIndex: isTop ? 10 : 10 - index,
      }}
      drag={isTop}
      dragConstraints={{ left: 0, right: 0, top: 0, bottom: 0 }}
      dragElastic={0.2}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      animate={{
        scale: isTop ? 1 : 0.95 - index * 0.02,
        y: isTop ? 0 : index * 4,
      }}
      transition={{
        type: "spring",
        stiffness: 300,
        damping: 30
      }}
      whileTap={{ scale: 0.98 }}
    >
      {/* Card Content */}
      <div className="h-full bg-white dark:bg-gray-800 rounded-3xl shadow-2xl overflow-hidden border border-gray-100 dark:border-gray-700">
        {/* Present Indicator */}
        <motion.div
          className="absolute inset-0 bg-green-500 flex items-center justify-center rounded-3xl"
          style={{ opacity: presentOpacity }}
          initial={false}
        >
          <div className="text-white text-4xl font-bold rotate-[-20deg]">
            ✅ ПРИСУТНІЙ
          </div>
        </motion.div>

        {/* Absent Indicator */}
        <motion.div
          className="absolute inset-0 bg-red-500 flex items-center justify-center rounded-3xl"
          style={{ opacity: absentOpacity }}
          initial={false}
        >
          <div className="text-white text-4xl font-bold rotate-[20deg]">
            ❌ ВІДСУТНІЙ
          </div>
        </motion.div>

        {/* Main Card Content */}
        <div className="h-full flex flex-col items-center justify-center p-8 text-center">
          {/* Avatar */}
          <div className="text-8xl mb-6">
            {getGenderEmoji(student.gender)}
          </div>

          {/* Name */}
          <h2 className="text-3xl font-bold text-gray-800 dark:text-gray-100 mb-2">
            {student.full_name}
          </h2>

          {/* Age */}
          <p className="text-xl text-gray-600 dark:text-gray-300 mb-4">
            {student.age} років • {getAgeGroup(student.age)}
          </p>

          {/* Badge */}
          <div className="inline-flex items-center px-4 py-2 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded-full text-sm font-medium">
            ID: {student.id}
          </div>

          {/* Drag indicators (only show when top card) */}
          {isTop && !isDragging && (
            <div className="absolute bottom-8 left-0 right-0 flex justify-center">
              <div className="bg-gray-900 dark:bg-gray-100 bg-opacity-80 text-white dark:text-gray-900 px-4 py-2 rounded-full text-sm font-medium">
                👆 Присутній • 👇 Відсутній • 👈👉 Пропустити
              </div>
            </div>
          )}

          {/* Drag hints (show when dragging) */}
          {isTop && isDragging && (
            <div className="absolute bottom-8 left-0 right-0 flex justify-center">
              <motion.div
                className="bg-gray-900 dark:bg-gray-100 bg-opacity-90 text-white dark:text-gray-900 px-4 py-2 rounded-full text-sm font-medium"
                animate={{ scale: [1, 1.05, 1] }}
                transition={{ repeat: Infinity, duration: 1 }}
              >
                🎯 Продовжуйте свайп...
              </motion.div>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}

export default SwipeCard
