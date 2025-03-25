import { useEffect, useState } from 'react'
import StudyActivity from '@/components/StudyActivity'
import { useParams } from 'react-router-dom'

type ActivityCard = {
  id: number
  name: string
  url: string
  preview_url: string
}

export default function StudyActivities() {
  const { groupId } = useParams()
  const [activities, setActivities] = useState<ActivityCard[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchActivities = async () => {
      try {
        const response = await fetch('http://localhost:5001/api/study-activities', {
          mode: 'cors'  // Change to port 5001
        });
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        setActivities(data);
        setLoading(false);
      } catch (err) {
        setError(err.message);
        setLoading(false);
      }
    };

    fetchActivities();
  }, []);

  if (loading) {
    return <div className="text-center">Loading study activities...</div>
  }

  if (error) {
    return <div className="text-red-500">Error: {error}</div>
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {activities.map((activity) => (
        <StudyActivity 
          key={activity.id} 
          activity={activity} 
          groupId={groupId ? parseInt(groupId) : undefined}
        />
      ))}
    </div>
  )
}