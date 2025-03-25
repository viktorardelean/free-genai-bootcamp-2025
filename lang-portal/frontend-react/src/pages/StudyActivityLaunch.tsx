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
    fetch(`http://localhost:5001/api/study-activities/${id}/launch`)
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
      // Get the launch URL from the activity data and add query parameters
      const launchUrl = new URL(launchData.activity.launch_url);
      launchUrl.searchParams.set('group_id', selectedGroup);
      
      // Open the modified URL in a new tab
      window.open(launchUrl.toString(), '_blank');
      
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
