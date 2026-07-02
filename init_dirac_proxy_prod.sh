# Create the proxy for iLCDirac
echo "Initializing the DIRAC/Grid proxy ..."
dirac-proxy-init -g fcc_prod
if test "x$?" = "x0" ; then
   echo "Done!"
   echo -e "\033[94mPlease note you are running with fcc_prod permissions\033[0m"
else
   echo "Some problem occured ..."
fi
