// Define a type for filter information used in the table
export type Filters = Record<string, string[]>;

// Define a type for the function that handles changes in the table (pagination, filters, sorter)
export type OnChange = (pagination: any, filters: Filters, sorter: any) => void;

// Define a type for filter dropdown props used in the table columns
export type FilterDropdownProps = {
  setSelectedKeys: (keys: React.Key[]) => void;
  selectedKeys: React.Key[];
  confirm: () => void;
  clearFilters?: () => void;
  close: () => void;
};

// Define a type for the data index, representing a key in the data object
export type DataIndex = string;

// Define a type for the table column properties
export type TableColumnsType<T> = {
  title: string;
  dataIndex: keyof T;
  key: string;
  ellipsis?: boolean;
  filters?: Array<{ text: string; value: string }>;
  filteredValue?: string[];
  filterSearch?: boolean;
  filterDropdown?: (props: FilterDropdownProps) => JSX.Element;
  filterIcon?: (filtered: boolean) => React.ReactNode;
  onFilter?: (value: string | number | boolean, record: T) => boolean;
  onFilterDropdownOpenChange?: (visible: boolean) => void;
  render?: (text: any, record: T) => JSX.Element;
}[];

// Define a type for the batches data
export interface IBatches {
  batch_id: string;
  batch_name: string;
  engagement: string;
  project: string;
  created_by: string;
}

// Define a type for error data
export interface ErrorData {
  message: string;
  status?: number;
}

// Define a type for the input reference used in the search functionality
export type InputRef = HTMLInputElement;

export interface IEngagement {
  name: string;
  description: string | null;
  id: number;
  created_at: string;
  updated_at: string;
}
