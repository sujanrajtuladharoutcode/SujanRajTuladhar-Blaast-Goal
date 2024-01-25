import React from 'react'
import './App.css';
import Register from './Components/Register';
import Login from './Components/Login';
import Navigate from './Components/Navigate';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import ChatArea from './Components/ChatArea';
import Sidebar from './Components/Sidebar';

function App() {
  return (
    <>
      <Sidebar/>
      <ChatArea/>
    </>
    // <BrowserRouter>
    //   <Navigate/>
    //   <Routes>
    //     <Route path='/register' element={<Register/>}>
    //     </Route>
    //     <Route path='/login' element={<Login/>}>
    //     </Route>
    //   </Routes>
    // </BrowserRouter>
  );
}

export default App;
