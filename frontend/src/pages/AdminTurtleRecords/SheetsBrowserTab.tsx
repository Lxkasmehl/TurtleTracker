import {
  Button,
  Card,
  Center,
  Divider,
  Grid,
  Paper,
  ScrollArea,
  Select,
  Stack,
  Text,
  TextInput,
} from '@mantine/core';
import { IconDatabase, IconMapPin, IconSearch } from '@tabler/icons-react';
import { TurtleSheetsDataForm } from '../../components/TurtleSheetsDataForm';
import { useAdminTurtleRecordsContext } from './AdminTurtleRecordsContext';

export function SheetsBrowserTab() {
  const ctx = useAdminTurtleRecordsContext();
  const {
    selectedSheetFilter,
    sheetsListLoading,
    availableSheets,
    searchQuery,
    setSearchQuery,
    loadAllTurtles,
    turtlesLoading,
    filteredTurtles,
    allTurtles,
    selectedTurtle,
    setSelectedTurtle,
    handleSaveTurtleFromBrowser: onSaveTurtle,
    setSelectedSheetFilterAndLoad: onSheetFilterChange,
  } = ctx;

  return (
    <Grid gutter='lg'>
      <Grid.Col span={{ base: 12, md: 4 }}>
        <Paper shadow='sm' p='md' radius='md' withBorder>
          <Stack gap='md'>
            <Text fw={500} size='lg'>
              Search & Filter
            </Text>
            <Select
              label='Location (Spreadsheet)'
              description={
                sheetsListLoading
                  ? 'Loading locations…'
                  : selectedSheetFilter
                    ? 'Only turtles from this sheet'
                    : 'All sheets'
              }
              placeholder='All locations'
              leftSection={<IconMapPin size={16} />}
              value={selectedSheetFilter}
              onChange={(value) => onSheetFilterChange(value ?? '')}
              data={[
                { value: '', label: 'All locations' },
                ...availableSheets.map((s) => ({ value: s, label: s })),
              ]}
              allowDeselect={false}
              searchable
              clearable={false}
              disabled={sheetsListLoading}
            />
            <TextInput
              placeholder='Search by ID, name, species, location...'
              leftSection={<IconSearch size={16} />}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <Button onClick={() => loadAllTurtles()} loading={turtlesLoading} fullWidth>
              Refresh
            </Button>
            <Divider />
            <Text size='sm' c='dimmed'>
              {filteredTurtles.length} of {allTurtles.length} turtles
            </Text>
            <ScrollArea h={600}>
              <Stack gap='xs'>
                {filteredTurtles.map((turtle, index) => (
                  <Card
                    key={`${turtle.primary_id || turtle.id || 'turtle'}-${index}-${turtle.sheet_name || ''}`}
                    shadow='sm'
                    padding='sm'
                    radius='md'
                    withBorder
                    style={{
                      cursor: 'pointer',
                      border:
                        selectedTurtle?.primary_id ===
                        (turtle.primary_id || turtle.id)
                          ? '2px solid #228be6'
                          : '1px solid #dee2e6',
                      backgroundColor:
                        selectedTurtle?.primary_id ===
                        (turtle.primary_id || turtle.id)
                          ? '#e7f5ff'
                          : 'white',
                    }}
                    onClick={() => setSelectedTurtle(turtle)}
                  >
                    <Stack gap={4}>
                      {turtle.name ? (
                        <Text fw={600} size='md' c='blue'>
                          {turtle.name}
                        </Text>
                      ) : (
                        <Text fw={500} size='sm' c='dimmed' fs='italic'>
                          No name
                        </Text>
                      )}

                      <Stack gap={2}>
                        {turtle.location && (
                          <Text size='sm' fw={500}>
                            📍 {turtle.location}
                          </Text>
                        )}
                        {turtle.species && (
                          <Text size='sm' c='dimmed'>
                            🐢 {turtle.species}
                          </Text>
                        )}
                      </Stack>

                      <Stack gap={2} mt='xs'>
                        {turtle.primary_id && (
                          <Text size='xs' c='dimmed'>
                            Primary ID: <strong>{turtle.primary_id}</strong>
                          </Text>
                        )}
                        {turtle.id && turtle.id !== turtle.primary_id && (
                          <Text size='xs' c='dimmed'>
                            ID: {turtle.id}
                          </Text>
                        )}
                        {!turtle.primary_id && !turtle.id && (
                          <Text size='xs' c='red' fs='italic'>
                            No ID
                          </Text>
                        )}
                      </Stack>
                    </Stack>
                  </Card>
                ))}
              </Stack>
            </ScrollArea>
          </Stack>
        </Paper>
      </Grid.Col>

      <Grid.Col span={{ base: 12, md: 8 }}>
        {selectedTurtle ? (
          <Paper shadow='sm' p='md' radius='md' withBorder>
            <ScrollArea h={700}>
              <TurtleSheetsDataForm
                initialData={selectedTurtle}
                sheetName={selectedTurtle.sheet_name}
                initialAvailableSheets={
                  availableSheets.length > 0 ? availableSheets : undefined
                }
                state={selectedTurtle.general_location || ''}
                location={selectedTurtle.location || ''}
                primaryId={
                  selectedTurtle.primary_id || selectedTurtle.id || undefined
                }
                mode='edit'
                onSave={onSaveTurtle}
              />
            </ScrollArea>
          </Paper>
        ) : (
          <Paper shadow='sm' p='xl' radius='md' withBorder>
            <Center py='xl'>
              <Stack gap='md' align='center'>
                <IconDatabase size={64} stroke={1.5} style={{ opacity: 0.3 }} />
                <Text size='lg' c='dimmed' ta='center'>
                  Select a turtle to edit
                </Text>
                <Text size='sm' c='dimmed' ta='center'>
                  Choose a turtle from the list to view and edit its Google Sheets
                  data
                </Text>
              </Stack>
            </Center>
          </Paper>
        )}
      </Grid.Col>
    </Grid>
  );
}
