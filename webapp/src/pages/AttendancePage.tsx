import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import CardStack from '../components/CardStack'
import { Group, Student, AttendanceSession, AttendanceEvent } from '../types'
import { useTelegramStore } from '../stores/telegramStore'
import { apiService } from '../utils/api'

const AttendancePage: React.FC = () => {
  const { groupId } = useParams<{ groupId: string }>()
  const navigate = useNavigate()
  const { hapticFeedback, showConfirm, setMainButton, hideMainButton } = useTelegramStore()
  
  const [loading, setLoading] = useState(true)
  const [group, setGroup] = useState<Group | null>(null)
  const [students, setStudents] = useState<Student[]>([])
  const [session, setSession] = useState<AttendanceSession | null>(null)
  const [pendingEvents, setPendingEvents] = useState<AttendanceEvent[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    if (groupId) {
      initializeSession()
    }
  }, [groupId])

  const initializeSession = async () => {
    try {
      setLoading(true)
      
      // Load group and students
      const [groupData, studentsData] = await Promise.all([
        apiService.getGroup(parseInt(groupId!)),
        apiService.getGroupStudents(parseInt(groupId!))
      ])

      setGroup(groupData)
      setStudents(studentsData)

      // Create attendance session
      const sessionData = await apiService.createSession({
        group_id: parseInt(groupId!)
      })
      
      setSession(sessionData)

      hapticFeedback('success')
      toast.success(`Розпочато відмітку для групи "${groupData.title}"`)

    } catch (error) {
      console.error('Failed to initialize session:', error)
      toast.error('Помилка ініціалізації сесії')
      navigate('/groups')
    } finally {
      setLoading(false)
    }
  }

  const handleAttendanceChange = (events: AttendanceEvent[]) => {
    setPendingEvents(events)
  }

  const handleComplete = async () => {
    if (pendingEvents.length === 0) {
      showConfirm(
        'Ви не відмітили жодного студента. Завершити сесію?',
        (confirmed) => {
          if (confirmed) {
            navigate('/groups')
          }
        }
      )
      return
    }

    showConfirm(
      `Відправити відмітку для ${pendingEvents.length} студентів?`,
      async (confirmed) => {
        if (confirmed) {
          await submitAttendance()
        }
      }
    )
  }

  const submitAttendance = async () => {
    if (!session || pendingEvents.length === 0) return

    try {
      setIsSubmitting(true)
      hideMainButton()

      // Submit attendance batch
      await apiService.submitAttendance({ events: pendingEvents })

      // End session
      await apiService.endSession(session.id)

      hapticFeedback('success')
      toast.success('Відмітку успішно відправлено!')

      // Navigate back after a short delay
      setTimeout(() => {
        navigate('/groups')
      }, 1500)

    } catch (error) {
      console.error('Failed to submit attendance:', error)
      toast.error('Помилка відправки даних')
      setIsSubmitting(false)
      
      // Restore main button
      setMainButton(
        `📝 Завершити (${pendingEvents.length}/${students.length})`,
        handleComplete
      )
    }
  }

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <motion.div
          className="text-center"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
        >
          <div className="text-4xl mb-4">📋</div>
          <p className="text-telegram-hint">Підготовка до відмітки...</p>
        </motion.div>
      </div>
    )
  }

  if (isSubmitting) {
    return (
      <div className="h-screen flex items-center justify-center">
        <motion.div
          className="text-center"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
        >
          <motion.div
            className="text-6xl mb-4"
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
          >
            📤
          </motion.div>
          <h3 className="text-xl font-semibold text-telegram-text mb-2">
            Відправляємо дані...
          </h3>
          <p className="text-telegram-hint">
            Збереження відміток у базі даних
          </p>
        </motion.div>
      </div>
    )
  }

  if (!group || !session) {
    return (
      <div className="h-screen flex items-center justify-center p-6">
        <div className="text-center">
          <div className="text-4xl mb-4">❌</div>
          <h3 className="text-xl font-semibold text-telegram-text mb-2">
            Помилка завантаження
          </h3>
          <p className="text-telegram-hint mb-4">
            Не вдалося завантажити дані групи
          </p>
          <button
            onClick={() => navigate('/groups')}
            className="bg-telegram-button text-telegram-button-text px-6 py-3 rounded-full font-medium"
          >
            Повернутися до груп
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      {/* Header */}
      <div className="safe-area-top bg-telegram-bg border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between p-4">
          <button
            onClick={() => {
              showConfirm(
                'Ви впевнені, що хочете вийти? Всі не збережені дані будуть втрачені.',
                (confirmed) => {
                  if (confirmed) {
                    navigate('/groups')
                  }
                }
              )
            }}
            className="text-telegram-link font-medium"
          >
            ← Назад
          </button>
          
          <div className="text-center">
            <h1 className="font-semibold text-telegram-text">
              {group.title}
            </h1>
            <p className="text-xs text-telegram-hint">
              {students.length} студентів
            </p>
          </div>
          
          <div className="w-16"></div> {/* Spacer for centering */}
        </div>
      </div>

      {/* Card Stack */}
      {session && (
        <CardStack
          students={students}
          sessionId={session.id}
          onAttendanceChange={handleAttendanceChange}
          onComplete={handleComplete}
        />
      )}
    </div>
  )
}

export default AttendancePage
