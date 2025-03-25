import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'

type ActivityProps = {
  activity: {
    id: number
    name: string
    url: string
    preview_url: string
  }
  groupId?: number
}

export default function StudyActivity({ activity, groupId }: ActivityProps) {
  return (
    <div className="bg-sidebar rounded-lg shadow-md overflow-hidden">
      <img src={activity.preview_url} alt={activity.name} className="w-full h-48 object-cover" />
      <div className="p-4">
        <h3 className="text-xl font-semibold mb-2">{activity.name}</h3>
        <div className="flex justify-between">
          <Button asChild>
            <Link 
              to={`/study-activities/${activity.id}/launch`}
              state={{ groupId }}
            >
              Launch
            </Link>
          </Button>
          <Button asChild variant="outline">
            <Link to={`/study-activities/${activity.id}`}>
              View
            </Link>
          </Button>
        </div>
      </div>
    </div>
  )
}