import { PageContainer } from "@/components/common/layout/PageContainer";
import { PageHeader } from "@/components/common/layout/PageHeader";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { WeeklyScheduleBuilder } from "./components/WeeklyScheduleBuilder";
import { ExceptionsList } from "./components/ExceptionsList";

export default function AvailabilitySettings() {
  return (
    <PageContainer>
      <PageHeader 
        title="Availability & Scheduling"
        description="Configure studio operating hours, blocked periods, and holidays."
      />

      <div className="mt-6">
        <Tabs defaultValue="weekly" className="space-y-6">
          <TabsList className="bg-slate-100">
            <TabsTrigger value="weekly">Weekly Schedule</TabsTrigger>
            <TabsTrigger value="exceptions">Overrides & Closures</TabsTrigger>
          </TabsList>

          <TabsContent value="weekly" className="m-0">
            <WeeklyScheduleBuilder />
          </TabsContent>

          <TabsContent value="exceptions" className="m-0">
            <ExceptionsList />
          </TabsContent>
        </Tabs>
      </div>
    </PageContainer>
  );
}