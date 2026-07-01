# Create the proxy for iLCDirac
echo "Initializing the DIRAC/Grid proxy ..."
dirac-proxy-init -g fcc_prod
if test "x$?" = "x0" ; then
   echo "Done!"
   echo "You're running with fcc_prod permissions"
else
   echo "Some problem occured ..."
fi
