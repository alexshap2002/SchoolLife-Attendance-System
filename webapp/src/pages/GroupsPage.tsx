import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import { Group, UserProfile } from '../types'
import { useTelegramStore } from '../stores/telegramStore'
import { apiService } from '../utils/api'

const GroupsPage: React.FC = () => {
  const navigate = useNavigate()
  const { user, hapticFeedback } = useTelegramStore()
  const [loading, setLoading] = useState(true)
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [groups, setGroups] = useState<Group[]>([])

  useEffect(() => {
    loadUserProfile()
  }, [])

  const loadUserProfile = async () => {
    try {
      setLoading(true)
      const userProfile = await apiService.getUserProfile()
      setProfile(userProfile)
      setGroups(userProfile.teacher_groups)
    } catch (error) {
      console.error('Failed to load profile:', error)
      toast.error('Помилка завантаження даних')
    } finally {
      setLoading(false)
    }
  }

  const handleGroupSelect = (group: Group) => {
    hapticFeedback('medium')
    navigate(`/attendance/${group.id}`)
  }

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-4xl mb-4">⏳</div>
          <p className="text-telegram-hint">Завантаження груп...</p>
        </div>
      </div>
    )
  }

  if (groups.length === 0) {
    return (
      <div className="h-screen flex items-center justify-center p-6">
        <motion.div
          className="text-center"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="text-6xl mb-4">👥</div>
          <h2 className="text-xl font-semibold text-telegram-text mb-2">
            Немає доступних груп
          </h2>
          <p className="text-telegram-hint">
            Зверніться до адміністратора для додавання груп
          </p>
        </motion.div>
      </div>
    )
  }

  return (
    <div className="h-screen overflow-y-auto safe-area-top safe-area-bottom">
      {/* Header */}
      <div className="sticky top-0 bg-telegram-bg border-b border-gray-200 dark:border-gray-700 z-10">
        <div className="p-6 pb-4">
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-center"
          >
            <h1 className="text-2xl font-bold text-telegram-text">
              📝 Відмітка присутності
            </h1>
            <p className="text-telegram-hint mt-1">
              Привіт, {user?.first_name || profile?.full_name}!
            </p>
          </motion.div>
        </div>
      </div>

      {/* Groups list */}
      <div className="p-6 space-y-4">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
        >
          <h2 className="text-lg font-semibold text-telegram-text mb-4">
            Оберіть групу для відмітки:
          </h2>
        </motion.div>

        {groups.map((group, index) => (
          <motion.div
            key={group.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 + index * 0.05 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => handleGroupSelect(group)}
            className="haptic-feedback"
          >
            <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm border border-gray-100 dark:border-gray-700 cursor-pointer transition-all hover:shadow-md active:shadow-sm">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-1">
                    {group.title}
                  </h3>
                  {group.description && (
                    <p className="text-gray-600 dark:text-gray-300 text-sm">
                      {group.description}
                    </p>
                  )}
                  <p className="text-gray-400 dark:text-gray-500 text-xs mt-2">
                    ID: {group.id}
                  </p>
                </div>
                <div className="flex items-center space-x-2 ml-4">
                  <div className="text-2xl">
                    👥
                  </div>
                  <div className="text-telegram-link">
                    <svg
                      className="w-6 h-6"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 5l7 7-7 7"
                      />
                    </svg>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Footer info */}
      <div className="p-6 text-center">
        <motion.p
          className="text-xs text-telegram-hint"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          School of Life Brusyliv • v1.0
        </motion.p>
      </div>
    </div>
  )
}

export default GroupsPage
