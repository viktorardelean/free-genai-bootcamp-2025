import { useState, useEffect } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useNavigation } from '@/context/NavigationContext'
import { createStudySession } from '@/services/api'

// Change API URL constant
const API_URL = import.meta.env.LANG_PORTAL_URL || 'http://localhost:5001'

type Group = {
  id: number
  name: string
}

type StudyActivity = {
  id: number
  title: string
  launch_url: string
  preview_url: string
}

type LaunchData = {
  activity: StudyActivity
  groups: Group[]
}

export default function StudyActivityLaunch() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { setCurrentStudyActivity } = useNavigation()
  const [launchData, setLaunchData] = useState<LaunchData | null>(null)
  const [selectedGroup, setSelectedGroup] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const location = useLocation()
  const { groupId } = location.state || {}

  useEffect(() => {
    fetch(`${API_URL}/api/study-activities/${id}/launch`)
      .then(response => {
        if (!response.ok) throw new Error('Failed to fetch launch data')
        return response.json()
      })
      .then(data => {
        setLaunchData(data)
        setCurrentStudyActivity(data.activity)
        setLoading(false)
      })
      .catch(err => {
        setError(err.message)
        setLoading(false)
      })
  }, [id, setCurrentStudyActivity])

  useEffect(() => {
    if (launchData?.activity.launch_url && groupId) {
      // Add group_id to the activity URL
      const activityUrl = new URL(launchData.activity.launch_url)
      activityUrl.searchParams.set('group_id', groupId.toString())
      window.location.href = activityUrl.toString()
    }
  }, [launchData, groupId])

  // Clean up when unmounting
  useEffect(() => {
    return () => {
      setCurrentStudyActivity(null)
    }
  }, [setCurrentStudyActivity])

  const handleLaunch = async () => {
    if (!launchData?.activity || !selectedGroup) return;
    
    try {
      // Create a new study session
      const response = await fetch(`${API_URL}/api/study_sessions`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          group_id: parseInt(selectedGroup, 10),
          study_activity_id: launchData.activity.id
        })
      });

      if (!response.ok) {
        throw new Error('Failed to create study session');
      }

      const session = await response.json();
      
      // Add session_id to the activity URL
      const activityUrl = new URL(launchData.activity.launch_url);
      activityUrl.searchParams.set('group_id', selectedGroup);
      activityUrl.searchParams.set('session_id', session.id.toString());
      
      // Open in new tab
      window.location.href = activityUrl.toString();

    } catch (error) {
      console.error('Failed to launch activity:', error);
      setError('Failed to launch activity. Please try again.');
    }
  }

  if (loading) {
    return <div className="text-center">Loading...</div>
  }

  if (error) {
    return <div className="text-red-500">Error: {error}</div>
  }

  if (!launchData) {
    return <div className="text-red-500">Activity not found</div>
  }

  // If no groupId was passed, show the group selector
  if (!groupId && !loading) {
    return (
      <div className="max-w-2xl mx-auto space-y-6">
        <h1 className="text-2xl font-bold">{launchData?.activity.title}</h1>
        
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Select Word Group</label>
            <Select onValueChange={setSelectedGroup} value={selectedGroup}>
              <SelectTrigger>
                <SelectValue placeholder="Select a word group" />
              </SelectTrigger>
              <SelectContent>
                {launchData?.groups.map((group) => (
                  <SelectItem key={group.id} value={group.id.toString()}>
                    {group.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <Button 
            onClick={handleLaunch}
            disabled={!selectedGroup}
            className="w-full"
          >
            Launch Now
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">{launchData.activity.title}</h1>
      
      <div className="space-y-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">Select Word Group</label>
          <Select onValueChange={setSelectedGroup} value={selectedGroup}>
            <SelectTrigger>
              <SelectValue placeholder="Select a word group" />
            </SelectTrigger>
            <SelectContent>
              {launchData.groups.map((group) => (
                <SelectItem key={group.id} value={group.id.toString()}>
                  {group.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <Button 
          onClick={handleLaunch}
          disabled={!selectedGroup}
          className="w-full"
        >
          Launch Now
        </Button>
      </div>
    </div>
  )
}
