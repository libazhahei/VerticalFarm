/**
 * Renders the dashboard content component.
 * This component displays various statistics and recent bookings in a grid layout.
 *
 * @component
 * @example
 * return (
 *   <DashboardContent />
 * )
 */
import React, { useEffect, useState } from 'react';
import {
  Grid,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  TablePagination,
} from '@mui/material';
import { sendRequest } from '../Request';
import DashboardProfit from './dashboardProfit';

const DashboardContent = () => {
  // State var
  const [recentBookings, setRecentBookings] = useState([]);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(5);
  const [dashboardData, setDashboardData] = useState([]);
  const [profitData, setProfitData] = useState([]);

  // Fetch data for dashboard
  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await sendRequest('user-admin/dashboard', 'GET', {});
        console.log('response dashboard', response);
        console.log('nook', response.recent_booking_trend);
        setDashboardData(response);
        setProfitData(response.recent_booking_trend);
        if (response && Array.isArray(response.recent_booking)) {
          // Ensure response contains a valid array
          setRecentBookings(response.recent_booking);
        } else {
          console.error(
            'No recent bookings data found or data is invalid:',
            response
          );
        }
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
      }
    };

    fetchData();
  }, []);

  // Sets new page
  const handleChangePage = (event, newPage) => {
    setPage(newPage);
  };

  // Adds row to table
  const handleChangeRowsPerPage = (event) => {
    setRowsPerPage(+event.target.value);
    setPage(0);
  };

  return (
    <Grid container spacing={3}>
      {/* Overview Cards */}
      <Grid item xs={12} sm={6} md={3}>
        <Card>
          <CardContent>
            <Typography variant="h6">Total Car Space</Typography>
            <Typography variant="h4">{dashboardData.total_carspace}</Typography>
          </CardContent>
        </Card>
      </Grid>
      <Grid item xs={12} sm={6} md={3}>
        <Card>
          <CardContent>
            <Typography variant="h6">Total Customers</Typography>
            <Typography variant="h4">{dashboardData.total_customer}</Typography>
          </CardContent>
        </Card>
      </Grid>
      <Grid item xs={12} sm={6} md={3}>
        <Card>
          <CardContent>
            <Typography variant="h6">Total Providers</Typography>
            <Typography variant="h4">{dashboardData.total_provider}</Typography>
          </CardContent>
        </Card>
      </Grid>
      <Grid item xs={12} sm={6} md={3}>
        <Card>
          <CardContent>
            <Typography variant="h6">Total Bookings</Typography>
            <Typography variant="h4">{dashboardData.total_booking}</Typography>
          </CardContent>
        </Card>
      </Grid>
      {/* Booking Summary */}
      <Grid item xs={12}>
        <DashboardProfit data={profitData} />
      </Grid>
      <Grid item xs={12}>
        <Card>
          <CardContent>
            <Typography variant="h6">Recent Bookings</Typography>
            <TableContainer component={Paper}>
              <Table aria-label="Recent bookings">
                <TableHead>
                  <TableRow>
                    <TableCell>Requester</TableCell>
                    <TableCell>Start Date</TableCell>
                    <TableCell>End Date</TableCell>
                    <TableCell align="right">Price</TableCell>
                    <TableCell align="right">Status</TableCell>
                    {/* ... other table headers as needed */}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {recentBookings
                    .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                    .map((booking) => (
                      <TableRow key={booking.uid}>
                        <TableCell component="th" scope="row">
                          {booking.customer.username}
                        </TableCell>
                        <TableCell>
                          {new Date(
                            booking.start_datetime * 1000
                          ).toLocaleString()}
                        </TableCell>
                        <TableCell>
                          {new Date(
                            booking.end_datetime * 1000
                          ).toLocaleString()}
                        </TableCell>
                        <TableCell align="right" sx={{ fontWeight: 'bold' }}>
                          ${booking.cost}
                        </TableCell>
                        <TableCell align="right">
                          <Typography
                            variant="body1"
                            sx={{
                              fontWeight: 'bold',
                              color:
                                booking.status === 'cancelled'
                                  ? '#00A1C3'
                                  : booking.status === 'blocked'
                                    ? '#F44336'
                                    : '#4CAF50',
                            }}
                          >
                            {booking.status === 'cancelled'
                              ? 'Cancelled'
                              : booking.status === 'blocked'
                                ? 'Blocked'
                                : 'Active'}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ))}
                  {/* No need for emptyRows logic if not used */}
                </TableBody>
              </Table>
              <TablePagination
                rowsPerPageOptions={[5, 10, 20]}
                component="div"
                count={recentBookings.length}
                rowsPerPage={rowsPerPage}
                page={page}
                onPageChange={handleChangePage}
                onRowsPerPageChange={handleChangeRowsPerPage}
              />
            </TableContainer>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
};

export default DashboardContent;
